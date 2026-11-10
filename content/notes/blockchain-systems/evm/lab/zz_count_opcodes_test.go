// Counts the opcodes of each geth instruction set (jump_table.go) and lists the
// precompiled contracts of each fork (contracts.go).
// Copied temporarily into go-ethereum/core/vm by lab/count_opcodes.sh, run, and removed.
package vm

import (
	"encoding/json"
	"fmt"
	"strings"
	"os"
	"reflect"
	"testing"
)

func fnptr(f any) uintptr {
	v := reflect.ValueOf(f)
	if !v.IsValid() || v.IsNil() {
		return 0
	}
	return v.Pointer()
}

func TestZZCountOpcodes(t *testing.T) {
	sets := []struct {
		name string
		jt   JumpTable
	}{
		{"Frontier", frontierInstructionSet}, {"Homestead", homesteadInstructionSet},
		{"Tangerine Whistle", tangerineWhistleInstructionSet}, {"Spurious Dragon", spuriousDragonInstructionSet},
		{"Byzantium", byzantiumInstructionSet}, {"Constantinople", constantinopleInstructionSet},
		{"Istanbul", istanbulInstructionSet}, {"Berlin", berlinInstructionSet},
		{"London", londonInstructionSet}, {"Merge", mergeInstructionSet},
		{"Shanghai", shanghaiInstructionSet}, {"Cancun", cancunInstructionSet},
		{"Prague", pragueInstructionSet}, {"Osaka", osakaInstructionSet},
		{"Amsterdam", amsterdamInstructionSet}, {"Bogota", bogotaInstructionSet},
	}
	type row struct {
		Fork    string   `json:"fork"`
		Defined int      `json:"defined"`
		Added   []string `json:"added"`
		Changed []string `json:"changed"`
	}
	var rows []row
	var prev *JumpTable
	for i := range sets {
		jt := &sets[i].jt
		r := row{Fork: sets[i].name, Added: []string{}, Changed: []string{}}
		for op := 0; op < 256; op++ {
			o := jt[op]
			if o.undefined || OpCode(op) == INVALID { // 0xFE is the designated invalid instruction
				continue
			}
			r.Defined++
			if prev == nil {
				continue
			}
			p := prev[op]
			if p.undefined {
				r.Added = append(r.Added, OpCode(op).String())
			} else if fnptr(p.execute) != fnptr(o.execute) || p.constantGas != o.constantGas ||
				fnptr(p.dynamicGas) != fnptr(o.dynamicGas) {
				name := OpCode(op).String()
				if OpCode(op) == PREVRANDAO {
					name = "PREVRANDAO" // geth still prints the pre-Merge name DIFFICULTY for 0x44
				}
				r.Changed = append(r.Changed, name)
			}
		}
		rows = append(rows, r)
		prev = jt
	}
	// Precompiled contracts of each fork (contracts.go).
	type pre struct {
		Fork      string            `json:"fork"`
		Contracts map[string]string `json:"contracts"`
	}
	var pres []pre
	for _, s := range []struct {
		name string
		set  PrecompiledContracts
	}{
		{"Homestead", PrecompiledContractsHomestead}, {"Byzantium", PrecompiledContractsByzantium},
		{"Istanbul", PrecompiledContractsIstanbul}, {"Berlin", PrecompiledContractsBerlin},
		{"Cancun", PrecompiledContractsCancun}, {"Prague", PrecompiledContractsPrague},
		{"Osaka", PrecompiledContractsOsaka},
	} {
		m := map[string]string{}
		for addr, c := range s.set {
			m["0x"+strings.TrimLeft(fmt.Sprintf("%x", addr.Bytes()), "0")] = strings.TrimPrefix(fmt.Sprintf("%T", c), "*vm.")
		}
		pres = append(pres, pre{s.name, m})
	}
	out := map[string]any{"instruction_sets": rows, "precompiles": pres}
	b, _ := json.MarshalIndent(out, "", "  ")
	if err := os.WriteFile(os.Getenv("OPCODES_OUT"), append(b, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}
