/*
 * keccak256 の先頭を n ビットに切った値で、2 種類の探索の回数を数える。
 *
 *   target <hex8> <n> <prefix> <suffix>
 *       名前 prefix0, prefix1, ... に suffix を付けた署名を順に試し、
 *       先頭 n ビットが hex8 の先頭 n ビットと一致した最初の番号を出す（狙った値）。
 *   collide <n> <seed> <suffix>
 *       名前 g<seed>_0, g<seed>_1, ... を順に試し、先頭 n ビットが
 *       それまでのどれかと一致した時点の試行回数と 2 つの名前を出す（どれでもよい 2 つ）。
 *
 * gcc -O3 -fopenmp -o selector_search selector_search.c
 */
#include <inttypes.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static const uint64_t RC[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808aULL, 0x8000000080008000ULL,
    0x000000000000808bULL, 0x0000000080000001ULL, 0x8000000080008081ULL, 0x8000000000008009ULL,
    0x000000000000008aULL, 0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL, 0x8000000000008089ULL, 0x8000000000008003ULL,
    0x8000000000008002ULL, 0x8000000000000080ULL, 0x000000000000800aULL, 0x800000008000000aULL,
    0x8000000080008081ULL, 0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL};
static const int ROT[24] = {1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44};
static const int PI[24] = {10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1};

#define ROTL(x, n) (((x) << (n)) | ((x) >> (64 - (n))))

static void keccak_f(uint64_t s[25]) {
    for (int r = 0; r < 24; r++) {
        uint64_t c[5], t;
        for (int i = 0; i < 5; i++) c[i] = s[i] ^ s[i + 5] ^ s[i + 10] ^ s[i + 15] ^ s[i + 20];
        for (int i = 0; i < 5; i++) {
            t = c[(i + 4) % 5] ^ ROTL(c[(i + 1) % 5], 1);
            for (int j = 0; j < 25; j += 5) s[i + j] ^= t;
        }
        t = s[1];
        for (int i = 0; i < 24; i++) {
            int p = PI[i];
            uint64_t u = s[p];
            s[p] = ROTL(t, ROT[i]);
            t = u;
        }
        for (int j = 0; j < 25; j += 5) {
            uint64_t b[5];
            for (int i = 0; i < 5; i++) b[i] = s[i + j];
            for (int i = 0; i < 5; i++) s[i + j] = b[i] ^ (~b[(i + 1) % 5] & b[(i + 2) % 5]);
        }
        s[0] ^= RC[r];
    }
}

/* 136 バイト未満の入力の keccak256 の先頭 4 バイトを、ビッグエンディアンの整数で返す */
static uint32_t selector(const char *msg, size_t len) {
    uint8_t block[136] = {0};
    memcpy(block, msg, len);
    block[len] = 0x01;
    block[135] |= 0x80;
    uint64_t s[25] = {0};
    for (int i = 0; i < 17; i++) {
        uint64_t w;
        memcpy(&w, block + 8 * i, 8);
        s[i] ^= w;
    }
    keccak_f(s);
    uint8_t *o = (uint8_t *)s;
    return ((uint32_t)o[0] << 24) | ((uint32_t)o[1] << 16) | ((uint32_t)o[2] << 8) | o[3];
}

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
    if (argc == 6 && strcmp(argv[1], "target") == 0) {
        uint32_t target = (uint32_t)strtoul(argv[2], NULL, 16);
        int n = atoi(argv[3]);
        uint32_t mask = n == 32 ? 0xffffffffu : ~((1u << (32 - n)) - 1);
        const char *prefix = argv[4], *suffix = argv[5];
        uint64_t found = UINT64_MAX;
        const uint64_t chunk = 1ULL << (n > 26 ? 20 : (n > 16 ? n - 6 : 10));
        double t0 = now();
        for (uint64_t base = 0; found == UINT64_MAX; base += chunk * 64) {
#pragma omp parallel for schedule(dynamic, 1) reduction(min : found)
            for (uint64_t c = 0; c < 64; c++) {
                char buf[136];
                for (uint64_t i = base + c * chunk; i < base + (c + 1) * chunk; i++) {
                    int len = snprintf(buf, sizeof buf, "%s%" PRIu64 "%s", prefix, i, suffix);
                    if ((selector(buf, len) & mask) == (target & mask)) {
                        if (i < found) found = i;
                        break;
                    }
                }
            }
        }
        char buf[136];
        int len = snprintf(buf, sizeof buf, "%s%" PRIu64 "%s", prefix, found, suffix);
        printf("n=%d tries=%" PRIu64 " seconds=%.2f threads=%d selector=%08x name=%s\n", n, found + 1,
               now() - t0, omp_get_max_threads(), selector(buf, len), buf);
        return 0;
    }
    if (argc == 5 && strcmp(argv[1], "collide") == 0) {
        int n = atoi(argv[2]);
        const char *seed = argv[3], *suffix = argv[4];
        uint32_t mask = n == 32 ? 0xffffffffu : ~((1u << (32 - n)) - 1);
        size_t cap = 1;
        while (cap < (1ULL << (n / 2 + 4))) cap <<= 1;
        uint64_t *idx = malloc(cap * sizeof *idx); /* 0 は空き。番号は 1 から */
        uint32_t *val = malloc(cap * sizeof *val);
        memset(idx, 0, cap * sizeof *idx);
        char buf[136];
        for (uint64_t i = 1;; i++) {
            int len = snprintf(buf, sizeof buf, "g%s_%" PRIu64 "%s", seed, i, suffix);
            uint32_t v = selector(buf, len) & mask;
            size_t h = (v * 2654435761u) & (cap - 1);
            while (idx[h] && val[h] != v) h = (h + 1) & (cap - 1);
            if (idx[h]) {
                char other[136];
                snprintf(other, sizeof other, "g%s_%" PRIu64 "%s", seed, idx[h], suffix);
                printf("n=%d tries=%" PRIu64 " selector=%08x a=%s b=%s\n", n, i, selector(buf, len), other, buf);
                return 0;
            }
            idx[h] = i;
            val[h] = v;
        }
    }
    fprintf(stderr, "usage: see the comment at the top of %s\n", argv[0]);
    return 2;
}
