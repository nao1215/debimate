// Package flowchart builds the deploy flow of a release as a mermaid flowchart.
package flowchart

import (
	"github.com/nao1215/markdown/mermaid/flowchart"
)

// Deploy returns the mermaid source of the deploy flow for release.
func Deploy(release string) string {
	return flowchart.NewFlowchart(nil, flowchart.WithTitle("Deploy "+release+" #prod")).
		NodeWithText("A", `run "make release"`).
		NodeWithText("B", "push the tag").
		LinkWithArrowHead("A", "B").
		String()
}
