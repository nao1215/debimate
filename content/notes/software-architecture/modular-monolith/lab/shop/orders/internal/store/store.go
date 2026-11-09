// Package store は注文モジュールの内部です。表の列（Status など）を持ちます。
package store

// Row は orders 表の 1 行です。
type Row struct {
	ID     string
	Total  int
	Status string
}

// Store は orders 表の代わりのメモリ上の表です。
type Store struct{ rows map[string]Row }

func New() *Store { return &Store{rows: map[string]Row{}} }

func (s *Store) Save(r Row) { s.rows[r.ID] = r }

func (s *Store) Find(id string) (Row, bool) {
	r, ok := s.rows[id]
	return r, ok
}
