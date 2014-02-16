#include <stdio.h>

int
test_ok(void * setup_ctxt) {
    printf("  (c) test_ok\n");
    return 1;
}

int
test_fail_expect_fail(void * setup_ctxt) {
    printf("  (c) test_fail_expect_fail\n");
    return 0;
}

int 
test_segfault_expect_err(void * setup_ctxt) {
    int * foo = NULL;
    printf("  (c) test_segfault\n");
    *foo = 99999;
    return 0;
}

int
tst_not_found(void * setup_ctxt) {
    printf("  (c) this test should not be found\n");
    return 0;
}

int 
testmatch_test_1(void * setup_ctxt) {
    printf("  (c) testmatch_test_1\n");
    return 1;
}

