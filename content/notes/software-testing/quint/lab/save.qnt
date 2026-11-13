// sqly の .save が複数のファイルを書き戻す手順の仕様。
// DESIGN で、2026-07-29 から 08-04 までの 7 つの設計を切り替える。
//   direct      : 各ファイルへ直接書く（220a85f より前）
//   staged      : 全部を一時ファイルに書いてから、1 つずつ rename で移す（220a85f）
//   copied      : rename を断られたら、コピーで上書きする（23dcc5a）
//   selfRestore : 上書きに失敗したら、そのファイル自身をバックアップから戻す（ff97dc2・0ee1d88）
//   rollback    : 移すのに失敗したら、移し終えた分を戻す。失敗したファイル自身は戻さず、
//                 戻せなくても黙る（3036574。selfRestore の戻しが消えた）
//   reported    : rollback に加え、戻せなかったファイルを報告する（663bd7a）
//   touched     : reported に加え、失敗したファイル自身も書き込み途中なら戻す（1742eca）
module saveproto {
  const DESIGN: str
  // 仕様に書く失敗の種類。COPY_CAN_FAIL: 上書きの途中で失敗する、RESTORE_CAN_FAIL: 戻すのに失敗する
  const COPY_CAN_FAIL: bool
  const RESTORE_CAN_FAIL: bool

  pure val TARGETS = ["a", "b"]
  pure val N = TARGETS.length()

  // ファイルの中身は old（保存前）、new（保存後）、broken（書き込み途中）の 3 つ
  var disk: str -> str
  // stage（一時ファイルに書く）→ commit（移す）→ ok か failed
  var phase: str
  var i: int
  // 戻せなかったと利用者に報告したファイル
  var reported: Set[str]
  // 表示用: 直前に起きたこと
  var event: { step: str, target: str, outcome: str }

  action init = all {
    disk' = Map("a" -> "old", "b" -> "old"),
    phase' = if (DESIGN == "direct") "commit" else "stage",
    i' = 0,
    reported' = Set(),
    event' = { step: "start", target: "", outcome: "" },
  }

  action stageStep = {
    nondet ok = Set(true, false).oneOf()
    all {
      phase == "stage",
      disk' = disk,
      reported' = reported,
      if (not(ok)) all {
        phase' = "failed", i' = i, event' = { step: "stage", target: TARGETS[i], outcome: "fail" },
      } else if (i + 1 == N) all {
        phase' = "commit", i' = 0, event' = { step: "stage", target: TARGETS[i], outcome: "ok" },
      } else all {
        phase' = "stage", i' = i + 1, event' = { step: "stage", target: TARGETS[i], outcome: "ok" },
      },
    }
  }

  // restoring に入ったファイルをバックアップから戻す。bad に入ったファイルは戻すのに失敗する
  pure def restore(d: str -> str, restoring: Set[str], bad: Set[str]): str -> str =
    d.keys().mapBy(f => if (restoring.contains(f) and not(bad.contains(f))) "old" else d.get(f))

  action commitStep = {
    // renamed: 移せた / renameFailed: 移せず、先は元のまま / copyFailed: 上書きの途中で失敗し、先は書きかけ
    nondet outcome = (if (COPY_CAN_FAIL) Set("renamed", "renameFailed", "copyFailed")
                      else Set("renamed", "renameFailed")).oneOf()
    nondet bad = (if (RESTORE_CAN_FAIL) TARGETS.indices().map(j => TARGETS[j]).powerset()
                  else Set(Set())).oneOf()
    val t = TARGETS[i]
    val touched = outcome == "copyFailed"
    val d1 = if (touched) disk.set(t, "broken") else disk
    // 戻す範囲: 設計ごとに違う。先頭から k 個か、失敗したファイル自身か
    val k =
      if (DESIGN == "rollback" or DESIGN == "reported") i
      else if (DESIGN == "touched") (if (touched) i + 1 else i)
      else 0
    val restoring =
      if (DESIGN == "selfRestore") (if (touched) Set(t) else Set())
      else TARGETS.indices().filter(j => j < k).map(j => TARGETS[j])
    val badHere = bad.intersect(restoring)
    all {
      phase == "commit",
      if (outcome == "renamed") all {
        disk' = disk.set(t, "new"),
        reported' = reported,
        phase' = if (i + 1 == N) "ok" else "commit",
        i' = if (i + 1 == N) i else i + 1,
        event' = { step: "commit", target: t, outcome: "renamed" },
      } else all {
        disk' = restore(d1, restoring, badHere),
        reported' = if (DESIGN == "reported" or DESIGN == "touched") badHere else reported,
        phase' = "failed",
        i' = i,
        event' = { step: "commit", target: t, outcome: outcome },
      },
    }
  }

  action done = all {
    Set("ok", "failed").contains(phase),
    disk' = disk, phase' = phase, i' = i, reported' = reported, event' = event,
  }

  action step = any { stageStep, commitStep, done }

  // 失敗した保存は、全てのファイルを元のままにするか、元に戻せなかったと報告する
  val failedSaveKeepsOld = phase == "failed" implies
    TARGETS.indices().forall(j => disk.get(TARGETS[j]) == "old" or reported.contains(TARGETS[j]))

  // 成功した保存は、全てのファイルを新しくする
  val okSaveWritesAll = phase == "ok" implies
    TARGETS.indices().forall(j => disk.get(TARGETS[j]) == "new")

  val atomic = failedSaveKeepsOld and okSaveWritesAll

  // 表紙の図のため: a の上書きが途中で失敗した直後に a が元の中身へ戻っている状態は「無い」と主張する。
  // verify がこれに違反するトレースを返せば、その設計は a を戻せる
  val noRestoreAfterCopyFailOnA =
    not(event.step == "commit" and event.target == "a" and event.outcome == "copyFailed"
        and disk.get("a") == "old")
}

module direct { import saveproto(DESIGN = "direct", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
// 220a85f にはコピーによる上書きが無いので、上書きの失敗は起きない
module staged { import saveproto(DESIGN = "staged", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = true).* }
module copied { import saveproto(DESIGN = "copied", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
module selfRestore { import saveproto(DESIGN = "selfRestore", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
module rollback { import saveproto(DESIGN = "rollback", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
module reported { import saveproto(DESIGN = "reported", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
module touched { import saveproto(DESIGN = "touched", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = true).* }
module rollback_renameOnly { import saveproto(DESIGN = "rollback", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = false).* }
module rollback_noRestoreFail { import saveproto(DESIGN = "rollback", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = false).* }
module rollback_noCopyFail { import saveproto(DESIGN = "rollback", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = true).* }
module reported_renameOnly { import saveproto(DESIGN = "reported", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = false).* }
module reported_noRestoreFail { import saveproto(DESIGN = "reported", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = false).* }
module reported_noCopyFail { import saveproto(DESIGN = "reported", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = true).* }
module touched_renameOnly { import saveproto(DESIGN = "touched", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = false).* }
module touched_noRestoreFail { import saveproto(DESIGN = "touched", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = false).* }
module selfRestore_renameOnly { import saveproto(DESIGN = "selfRestore", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = false).* }
module selfRestore_noRestoreFail { import saveproto(DESIGN = "selfRestore", COPY_CAN_FAIL = true, RESTORE_CAN_FAIL = false).* }
module selfRestore_noCopyFail { import saveproto(DESIGN = "selfRestore", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = true).* }
module touched_noCopyFail { import saveproto(DESIGN = "touched", COPY_CAN_FAIL = false, RESTORE_CAN_FAIL = true).* }
