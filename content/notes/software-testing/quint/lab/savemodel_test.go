package shell

// .save の失敗の順番を、本物の writeBack に差し込むテスト。
// TestSaveReplaysQuintTraces は Quint が書き出した ITF の trace を再生し、
// TestSaveRapidFaults は同じ失敗を rapid に引かせる。

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"testing"

	"pgregory.net/rapid"
)

// faultPlan は、2 つの対象（a = people.csv、b = places.csv）に起きる失敗。
type faultPlan struct {
	stageFail   string            // "a" / "b" / ""（一時ファイルの作成で失敗する対象）
	commit      map[string]string // 対象 → renamed / renameFailed / copyFailed
	restoreFail map[string]bool   // backup から戻すのに失敗する対象
}

type saveResult struct {
	disk map[string]string // 対象 → old / new / broken
	err  error
}

var saveTargets = []string{"a", "b"}

const (
	peopleOld = "id,name\n1,alice\n"
	placesOld = "id,city\n1,tokyo\n"
)

// runSave は 2 つの CSV を取り込み、両方を UPDATE してから .save --in-place を
// plan の通りに失敗させ、各ファイルが old / new / broken のどれかを返す。
func runSave(t *testing.T, plan faultPlan) saveResult {
	dir := t.TempDir()
	files := map[string]string{
		"a": writeCSV(t, dir, "people.csv", peopleOld),
		"b": writeCSV(t, dir, "places.csv", placesOld),
	}
	old := map[string]string{"a": peopleOld, "b": placesOld}
	byPath := map[string]string{files["a"]: "a", files["b"]: "b"}

	s, cleanup := writeBackShell(t, files["a"], files["b"])
	defer cleanup()
	silenceStderr(t)
	ctx := context.Background()
	for _, stmt := range []string{"UPDATE people SET name = 'zed'", "UPDATE places SET city = 'osaka'"} {
		if err := s.exec(ctx, stmt); err != nil {
			t.Fatalf("%s: %v", stmt, err)
		}
	}

	ops := defaultFileOps()
	s.files = ops
	lastStat := ""
	s.files.CreateTemp = func(d, pattern string) (*os.File, error) {
		if strings.Contains(pattern, ".sqly-save-") {
			target := byPath[filepath.Join(d, strings.SplitN(strings.TrimPrefix(pattern, "."), ".sqly-save-", 2)[0])]
			if plan.stageFail == target {
				return nil, errInjected
			}
		}
		return ops.CreateTemp(d, pattern)
	}
	s.files.Stat = func(name string) (os.FileInfo, error) {
		if _, ok := byPath[name]; ok {
			lastStat = name
		}
		return ops.Stat(name)
	}
	// 権限のコピーで失敗する = 先を触る前に失敗する
	s.files.Chmod = func(name string, mode os.FileMode) error {
		if plan.commit[byPath[lastStat]] == "renameFailed" {
			return errInjected
		}
		return ops.Chmod(name, mode)
	}
	s.files.Rename = func(oldpath, newpath string) error {
		if plan.commit[byPath[newpath]] == "copyFailed" {
			return errors.New("rename refused, as on Windows")
		}
		return ops.Rename(oldpath, newpath)
	}
	s.files.Copy = func(src, dest string) error {
		target, toTarget := byPath[dest]
		base := filepath.Base(src)
		switch {
		case toTarget && strings.Contains(base, ".sqly-save-") && plan.commit[target] == "copyFailed":
			// 上書きの途中で失敗する: 先を切り詰め、頭だけ書いて止まる
			return truncatingCopy(ops.Copy, 1, "id,", errInjected)(src, dest)
		case toTarget && strings.Contains(base, ".sqly-bak") && plan.restoreFail[target]:
			return errors.New("restore refused")
		}
		return ops.Copy(src, dest)
	}

	err := s.writeBack(ctx, "", false)
	disk := map[string]string{}
	for _, tgt := range saveTargets {
		got := readFile(t, files[tgt])
		switch {
		case got == old[tgt]:
			disk[tgt] = "old"
		case strings.Contains(got, "zed") || strings.Contains(got, "osaka"):
			disk[tgt] = "new"
		default:
			disk[tgt] = "broken"
		}
	}
	return saveResult{disk: disk, err: err}
}

// saveIsAtomic は Quint の仕様の不変条件と同じ: 失敗した保存は、全てのファイルを
// 元のままにするか、元に戻せなかったファイルを rollback のエラーで名指しする。
// weak にすると、エラーの文にファイル名があるだけで良しとする（最初に書いた判定）。
func saveIsAtomic(r saveResult, weak bool) error {
	names := map[string]string{"a": "people.csv", "b": "places.csv"}
	restoreFailed := map[string]bool{}
	var walk func(error)
	walk = func(err error) {
		if err == nil {
			return
		}
		var op *fileOpError
		if errors.As(err, &op) && op.Op == opRollback {
			restoreFailed[filepath.Base(op.Path)] = true
		}
		switch u := err.(type) {
		case interface{ Unwrap() []error }:
			for _, e := range u.Unwrap() {
				walk(e)
			}
		case interface{ Unwrap() error }:
			walk(u.Unwrap())
		}
	}
	walk(r.err)
	for _, tgt := range saveTargets {
		name := names[tgt]
		if r.err == nil && r.disk[tgt] != "new" {
			return fmt.Errorf("save succeeded but %s is %s", name, r.disk[tgt])
		}
		if r.err == nil || r.disk[tgt] == "old" {
			continue
		}
		if weak && strings.Contains(r.err.Error(), name) {
			continue
		}
		if !weak && restoreFailed[name] {
			continue
		}
		return fmt.Errorf("save failed, %s is %s and no restore failure names it: %v", name, r.disk[tgt], r.err)
	}
	return nil
}

// ---- ITF の trace を読む（Go には Quint Connect が無いので自分で書く） ----

type itfTrace struct {
	States []map[string]json.RawMessage `json:"states"`
}

type itfEvent struct {
	Step    string `json:"step"`
	Target  string `json:"target"`
	Outcome string `json:"outcome"`
}

func itfVar(state map[string]json.RawMessage, name string) json.RawMessage {
	for k, v := range state {
		if strings.HasSuffix(k, "::"+name) {
			return v
		}
	}
	return nil
}

func itfStringMap(raw json.RawMessage) (map[string]string, error) {
	var m struct {
		Pairs [][2]string `json:"#map"`
	}
	if err := json.Unmarshal(raw, &m); err != nil {
		return nil, err
	}
	out := map[string]string{}
	for _, p := range m.Pairs {
		out[p[0]] = p[1]
	}
	return out, nil
}

func itfStringSet(raw json.RawMessage) ([]string, error) {
	var s struct {
		Items []string `json:"#set"`
	}
	if err := json.Unmarshal(raw, &s); err != nil {
		return nil, err
	}
	sort.Strings(s.Items)
	return s.Items, nil
}

// planFromTrace は trace の event から失敗の計画を、最後の状態から
// 仕様が期待するファイルの中身と、報告されるべきファイルを取り出す。
func planFromTrace(tr itfTrace) (faultPlan, map[string]string, []string, error) {
	plan := faultPlan{commit: map[string]string{}, restoreFail: map[string]bool{}}
	for _, st := range tr.States {
		var ev itfEvent
		if err := json.Unmarshal(itfVar(st, "event"), &ev); err != nil {
			return plan, nil, nil, err
		}
		switch {
		case ev.Step == "stage" && ev.Outcome == "fail":
			plan.stageFail = ev.Target
		case ev.Step == "commit":
			plan.commit[ev.Target] = ev.Outcome
		}
	}
	last := tr.States[len(tr.States)-1]
	disk, err := itfStringMap(itfVar(last, "disk"))
	if err != nil {
		return plan, nil, nil, err
	}
	reported, err := itfStringSet(itfVar(last, "reported"))
	if err != nil {
		return plan, nil, nil, err
	}
	for _, f := range reported {
		plan.restoreFail[f] = true
	}
	return plan, disk, reported, nil
}

func TestSaveReplaysQuintTraces(t *testing.T) {
	dir := os.Getenv("QUINT_TRACES")
	if dir == "" {
		t.Skip("QUINT_TRACES is not set")
	}
	paths, err := filepath.Glob(filepath.Join(dir, "*.itf.json"))
	if err != nil || len(paths) == 0 {
		t.Fatalf("no traces in %s: %v", dir, err)
	}
	sort.Strings(paths)
	failures := 0
	for _, p := range paths {
		data, err := os.ReadFile(p) //nolint:gosec // test input
		if err != nil {
			t.Fatal(err)
		}
		var tr itfTrace
		if err := json.Unmarshal(data, &tr); err != nil {
			t.Fatalf("%s: %v", p, err)
		}
		plan, want, reported, err := planFromTrace(tr)
		if err != nil {
			t.Fatalf("%s: %v", p, err)
		}
		got := runSave(t, plan)
		var problems []string
		for _, tgt := range saveTargets {
			if got.disk[tgt] != want[tgt] {
				problems = append(problems, fmt.Sprintf("%s: spec %s, sqly %s", tgt, want[tgt], got.disk[tgt]))
			}
		}
		if e := saveIsAtomic(got, false); e != nil {
			problems = append(problems, e.Error())
		}
		if len(problems) > 0 {
			failures++
			if failures <= 3 {
				t.Errorf("%s plan=%+v reported=%v: %s", filepath.Base(p), plan, reported, strings.Join(problems, "; "))
			}
		}
	}
	t.Logf("replayed %d traces, %d disagreed with the spec", len(paths), failures)
}

func TestSaveRapidFaults(t *testing.T) {
	rapid.Check(t, func(rt *rapid.T) {
		plan := faultPlan{commit: map[string]string{}, restoreFail: map[string]bool{}}
		plan.stageFail = rapid.SampledFrom([]string{"", "", "a", "b"}).Draw(rt, "stageFail")
		for _, tgt := range saveTargets {
			plan.commit[tgt] = rapid.SampledFrom([]string{"renamed", "renameFailed", "copyFailed"}).Draw(rt, "commit_"+tgt)
			plan.restoreFail[tgt] = rapid.Bool().Draw(rt, "restoreFail_"+tgt)
		}
		r := runSave(t, plan)
		if err := saveIsAtomic(r, os.Getenv("WEAK_ORACLE") != ""); err != nil {
			rt.Fatalf("plan %+v: disk %v: %v", plan, r.disk, err)
		}
	})
}

// TestSaveShowOneRun は、a の上書きが途中で失敗する 1 回を実行し、ファイルの中身とエラー文と
// 2 つの判定の結果を出す（SAVE_SHOW=1 の時だけ）。
func TestSaveShowOneRun(t *testing.T) {
	if os.Getenv("SAVE_SHOW") == "" {
		t.Skip("SAVE_SHOW is not set")
	}
	r := runSave(t, faultPlan{commit: map[string]string{"a": "copyFailed"}, restoreFail: map[string]bool{}})
	msg := regexp.MustCompile(`/[^ :]+/`).ReplaceAllString(r.err.Error(), "")
	t.Logf("disk: people.csv=%s places.csv=%s", r.disk["a"], r.disk["b"])
	t.Logf("error: %s", msg)
	t.Logf("weak oracle (the error names the file): %v", saveIsAtomic(r, true) == nil)
	t.Logf("precise oracle (a restore failure names the file): %v", saveIsAtomic(r, false) == nil)
}
