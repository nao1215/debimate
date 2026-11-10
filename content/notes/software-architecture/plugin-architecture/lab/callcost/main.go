// Command callcost measures how long one call to an Exporter takes
// when the plugin runs in the same process and when it runs in a child process.
//
//   - in-process: the core looks the Exporter up in a registry (map of
//     interface values) and calls Export directly.
//   - pipe: the plugin is a child process. The core writes a 4-byte length and
//     the payload to the child's stdin and waits for a 1-byte reply on stdout.
//   - net/rpc: the plugin is a child process serving net/rpc (gob encoding)
//     over a Unix domain socket, the shape used by RPC-based plugin systems.
//
// The child is this same binary started with the argument "pipe-child" or
// "rpc-child". Every call is synchronous: the core waits for the reply before
// sending the next request. The payload sizes are 16 B, 1 KiB and 64 KiB.
// For each size and mode the program runs the calls 9 times and prints the
// median of the per-call averages.
//
// Run: go run . (in this directory). Go 1.26, Linux.
package main

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"net/rpc"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"time"
)

// Exporter is the boundary from the note.
type Exporter interface {
	Export(data []byte) error
}

type countExporter struct{ n int }

func (c *countExporter) Export(data []byte) error {
	c.n += len(data)
	return nil
}

var registry = map[string]Exporter{"count": &countExporter{}}

// pipeExporter forwards Export to a child process over stdin/stdout.
type pipeExporter struct {
	w   *bufio.Writer
	r   *bufio.Reader
	hdr [4]byte
}

func (p *pipeExporter) Export(data []byte) error {
	binary.LittleEndian.PutUint32(p.hdr[:], uint32(len(data)))
	if _, err := p.w.Write(p.hdr[:]); err != nil {
		return err
	}
	if _, err := p.w.Write(data); err != nil {
		return err
	}
	if err := p.w.Flush(); err != nil {
		return err
	}
	_, err := p.r.ReadByte() // wait for the child's ack
	return err
}

// Plugin is the net/rpc service in the child.
type Plugin struct{ n int }

func (p *Plugin) Export(data []byte, reply *int) error {
	p.n += len(data)
	*reply = len(data)
	return nil
}

type rpcExporter struct{ c *rpc.Client }

func (r *rpcExporter) Export(data []byte) error {
	var reply int
	return r.c.Call("Plugin.Export", data, &reply)
}

func pipeChild() {
	r := bufio.NewReaderSize(os.Stdin, 1<<17)
	w := bufio.NewWriter(os.Stdout)
	var hdr [4]byte
	buf := make([]byte, 1<<17)
	n := 0
	for {
		if _, err := io.ReadFull(r, hdr[:]); err != nil {
			return
		}
		size := binary.LittleEndian.Uint32(hdr[:])
		if _, err := io.ReadFull(r, buf[:size]); err != nil {
			return
		}
		n += int(size)
		w.WriteByte(1)
		w.Flush()
	}
}

func rpcChild(sock string) {
	if err := rpc.Register(&Plugin{}); err != nil {
		panic(err)
	}
	l, err := net.Listen("unix", sock)
	if err != nil {
		panic(err)
	}
	fmt.Println("ready")
	conn, err := l.Accept()
	if err != nil {
		panic(err)
	}
	rpc.ServeConn(conn)
}

func measure(e Exporter, data []byte, calls int) float64 {
	const repeats = 9
	per := make([]float64, 0, repeats)
	for range repeats {
		start := time.Now()
		for range calls {
			if err := e.Export(data); err != nil {
				panic(err)
			}
		}
		per = append(per, float64(time.Since(start).Nanoseconds())/float64(calls))
	}
	slices.Sort(per)
	return per[repeats/2]
}

func main() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "pipe-child":
			pipeChild()
			return
		case "rpc-child":
			rpcChild(os.Args[2])
			return
		}
	}
	self, err := os.Executable()
	if err != nil {
		panic(err)
	}

	// pipe child
	pc := exec.Command(self, "pipe-child")
	stdin, _ := pc.StdinPipe()
	stdout, _ := pc.StdoutPipe()
	if err := pc.Start(); err != nil {
		panic(err)
	}
	pipe := &pipeExporter{w: bufio.NewWriterSize(stdin, 1<<17), r: bufio.NewReader(stdout)}

	// net/rpc child
	dir, err := os.MkdirTemp("", "callcost")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	sock := filepath.Join(dir, "plugin.sock")
	rc := exec.Command(self, "rpc-child", sock)
	rout, _ := rc.StdoutPipe()
	if err := rc.Start(); err != nil {
		panic(err)
	}
	if line, _ := bufio.NewReader(rout).ReadString('\n'); line != "ready\n" {
		panic("rpc child did not start")
	}
	client, err := rpc.Dial("unix", sock)
	if err != nil {
		panic(err)
	}
	rpcE := &rpcExporter{c: client}

	inproc := registry["count"]
	fmt.Println("ns per call (median of 9 runs)")
	fmt.Printf("%-8s %14s %14s %14s\n", "payload", "in-process", "pipe", "net/rpc+unix")
	for _, size := range []int{16, 1024, 65536} {
		data := make([]byte, size)
		fmt.Printf("%-8d %14.1f %14.0f %14.0f\n", size,
			measure(inproc, data, 20_000_000),
			measure(pipe, data, 20_000),
			measure(rpcE, data, 20_000))
	}

	client.Close()
	rc.Process.Kill()
	rc.Wait()
	stdin.Close()
	pc.Wait()
}
