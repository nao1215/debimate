/* Time two 32-byte comparisons, then recover a secret from the timing alone. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <x86intrin.h>

#define LEN 32
#define REPS 16 /* calls per sample: one call is shorter than the timer step */
#define PROFILE_SAMPLES 100000
#define MAX_SAMPLES 300
#define RUNS 20

typedef int (*equal_fn)(const uint8_t *, const uint8_t *);

__attribute__((noinline)) int early_exit_equal(const uint8_t *a, const uint8_t *b) {
    for (size_t i = 0; i < LEN; i++) {
        if (a[i] != b[i]) {
            return 0; /* returns as soon as one byte differs */
        }
    }
    return 1;
}

__attribute__((noinline)) int constant_time_equal(const uint8_t *a, const uint8_t *b) {
    uint8_t diff = 0;
    for (size_t i = 0; i < LEN; i++) {
        diff |= a[i] ^ b[i]; /* always reads every byte */
    }
    return diff == 0;
}

static uint64_t measure(equal_fn eq, const uint8_t *secret, const uint8_t *guess) {
    unsigned int aux;
    _mm_lfence();
    uint64_t start = __rdtscp(&aux);
    for (int i = 0; i < REPS; i++) {
        volatile int r = eq(secret, guess);
        (void)r;
    }
    uint64_t end = __rdtscp(&aux);
    _mm_lfence();
    return end - start;
}

static int cmp_u64(const void *x, const void *y) {
    uint64_t a = *(const uint64_t *)x, b = *(const uint64_t *)y;
    return (a > b) - (a < b);
}

/* Mean of the fastest 90%: drops samples hit by interrupts or context switches. */
static double trimmed_mean(uint64_t *v, int n) {
    qsort(v, n, sizeof(uint64_t), cmp_u64);
    double sum = 0;
    int keep = n * 9 / 10;
    for (int i = 0; i < keep; i++) sum += v[i];
    return sum / keep;
}

static double tsc_ticks_per_ns(void) {
    struct timespec a, b;
    unsigned int aux;
    clock_gettime(CLOCK_MONOTONIC, &a);
    uint64_t t0 = __rdtscp(&aux);
    do {
        clock_gettime(CLOCK_MONOTONIC, &b);
    } while ((b.tv_sec - a.tv_sec) * 1000000000L + (b.tv_nsec - a.tv_nsec) < 200000000L);
    uint64_t t1 = __rdtscp(&aux);
    return (t1 - t0) / ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec));
}

static uint8_t secret[LEN] __attribute__((aligned(64)));
static uint8_t guess[LEN] __attribute__((aligned(64)));
static uint64_t samples[256][MAX_SAMPLES];
#define STEPS (LEN / 4 + 1) /* prefix = 0, 4, ..., 32 */
static uint8_t prefixed[STEPS][LEN] __attribute__((aligned(64)));
static uint64_t profile[2][STEPS][PROFILE_SAMPLES];

/* Guess one byte at a time: the candidate that makes the comparison slowest wins. */
static int recover(equal_fn eq, int n) {
    memset(guess, 0, LEN);
    for (int pos = 0; pos < LEN - 1; pos++) {
        for (int s = 0; s < n; s++) {
            for (int c = 0; c < 256; c++) {
                int v = (c + s * 37) & 0xff; /* change the order every round */
                guess[pos] = (uint8_t)v;
                samples[v][s] = measure(eq, secret, guess);
            }
        }
        int best = 0;
        double best_time = 0;
        for (int c = 0; c < 256; c++) {
            double t = trimmed_mean(samples[c], n);
            if (t > best_time) {
                best_time = t;
                best = c;
            }
        }
        guess[pos] = (uint8_t)best;
    }
    /* The last byte barely changes the time, but a correct guess is accepted. */
    for (int c = 0; c < 256; c++) {
        guess[LEN - 1] = (uint8_t)c;
        if (eq(secret, guess)) return 1;
    }
    return 0;
}

int main(void) {
    equal_fn funcs[2] = {early_exit_equal, constant_time_equal};
    const char *names[2] = {"early_exit", "constant_time"};
    double tpn = tsc_ticks_per_ns();
    printf("# tsc_ticks_per_ns=%.3f\n", tpn);

    /* 1. Time per call for each length of matching prefix. */
    srand(1);
    for (int i = 0; i < LEN; i++) secret[i] = (uint8_t)(rand() & 0xff);
    for (int k = 0; k < STEPS; k++) {
        memcpy(prefixed[k], secret, LEN);
        if (k * 4 < LEN) prefixed[k][k * 4] ^= 0x01; /* first mismatch at byte k*4 */
    }
    for (int s = 0; s < PROFILE_SAMPLES; s++) { /* interleave to spread clock drift */
        for (int f = 0; f < 2; f++) {
            for (int k = 0; k < STEPS; k++) profile[f][k][s] = measure(funcs[f], secret, prefixed[k]);
        }
    }
    printf("func,prefix,ns_per_call\n");
    for (int f = 0; f < 2; f++) {
        for (int k = 0; k < STEPS; k++) {
            printf("%s,%d,%.2f\n", names[f], k * 4,
                   trimmed_mean(profile[f][k], PROFILE_SAMPLES) / tpn / REPS);
        }
    }

    /* 2. Recover random secrets from timing only. */
    printf("func,samples_per_candidate,recovered\n");
    int counts[4] = {10, 30, 100, MAX_SAMPLES};
    for (int f = 0; f < 2; f++) {
        for (int k = 0; k < 4; k++) {
            int ok = 0;
            for (int run = 0; run < RUNS; run++) {
                srand(100 + run);
                for (int i = 0; i < LEN; i++) secret[i] = (uint8_t)(rand() & 0xff);
                ok += recover(funcs[f], counts[k]);
            }
            printf("%s,%d,%d/%d\n", names[f], counts[k], ok, RUNS);
        }
    }
    return 0;
}
