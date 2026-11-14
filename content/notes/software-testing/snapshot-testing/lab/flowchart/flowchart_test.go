package flowchart

import (
	"os"
	"testing"
)

// TestDeployGolden compares the generated flowchart with testdata/deploy.mmd.
// Run with UPDATE_GOLDEN=1 to (re)write the golden file.
func TestDeployGolden(t *testing.T) {
	got := Deploy("v1.0")
	const path = "testdata/deploy.mmd"
	if os.Getenv("UPDATE_GOLDEN") != "" {
		if err := os.WriteFile(path, []byte(got), 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	want, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(want) != got {
		t.Errorf("golden mismatch\n--- want\n%s\n--- got\n%s", want, got)
	}
}
