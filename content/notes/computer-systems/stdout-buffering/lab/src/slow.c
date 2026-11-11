#include <stdio.h>
#include <unistd.h>

int main(void) {
    for (int i = 1; i <= 5; i++) {
        printf("line %d\n", i);
        usleep(500000); /* 0.5 秒 */
    }
    return 0;
}
