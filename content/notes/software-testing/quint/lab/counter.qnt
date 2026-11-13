module counter {
  var n: int
  action init = n' = 0
  action step = any { n' = n + 1, n' = n - 1 }
  val small = n < 3
}
