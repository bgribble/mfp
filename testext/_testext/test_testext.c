#include <stdio.h>

int 
testext_setup(void) {
	/* should be called with each test */ 
	printf("  (c) testext_setup\n");
	return 1;
}

int 
testext_teardown(void) {
	printf("  (c) testext_teardown\n");
	return 1;
}

int
testext_test_ok(void) {
	printf("  (c) testext_test_ok\n");
	return 1;
}

int
testext_test_fail(void) {
	printf("  (c) testext_test_fail (should fail)\n");
	return 0;
}

int
testext_test_fail_expect_fail(void) {
	printf("  (c) testext_test_fail_expect_fail\n");
	return 0;
}

int 
testext_segfault_expect_err(void) {
	int	* foo = NULL;
	printf("  (c) testext_segfault\n");
	*foo = 99999;
	return 0;
}

char
testext_returntype_expect_err(void) {
	printf("  (c) testext_test_returntype_expect_err\n");
	return (char)1;
}

int
testext_arity_expect_err(int arg1, int arg2) {
	printf("  (c) testext_test_returntype_expect_err\n");
	return 1;
}

int
test_not_found(void) {
	printf("  (c) this test should not be found\n");
	return 0;
}

int 
testmatch_test_1(void) {
	printf("  (c) testmatch_test_1\n");
	return 1;
}

