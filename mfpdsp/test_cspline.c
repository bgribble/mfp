#include <math.h>
#include <stdio.h>
#include <sys/time.h>
#include "cspline.h"
#include "mfp_block.h"

int
test_cspline_create(void)
{
	cspline * c = cspline_new(4, 8);
	mfp_block * in = mfp_block_new(8);
	mfp_block * out = mfp_block_new(8);
	int i;
	int fail = 0;
	float coeff_1[] = { 1.0, 0.0, 0.0, 0.0, 
		                2.0, 0.0, 0.0, 0.0,
		                3.0, 0.0, 0.0, 0.0,
		                4.0, 0.0, 0.0, 0.0 };
	float answers_1[] = { 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0 };

	float coeff_2[] = { 0.0, 1.0, 0.0, 0.0, 
		                0.0, 2.0, 0.0, 0.0,
		                0.0, 3.0, 0.0, 0.0,
		                0.0, 4.0, 0.0, 0.0 };
	float answers_2[] = { 0.0, 0.25, 1.0, 1.50, 3.0, 3.75, 6.0, 7.0 };

	if((c == NULL) || (c->num_segments != 4))
		return 0;

	cspline_init(c, 0.0, 2.0, coeff_1);
	for (i=0; i<8; i++) {
		in->data[i] = (float)i / 4.0;
	}

	cspline_block_eval(c, in, out);

	for (i=0; i<8; i++) {
		if (out->data[i] != answers_1[i]) {
			printf("err %d %f %f\n", i, out->data[i], answers_1[i]);
			fail = 1;
		}
	}

	cspline_init(c, 0.0, 2.0, coeff_2);
	for (i=0; i<8; i++) {
		in->data[i] = (float)i / 4.0;
	}

	cspline_block_eval(c, in, out);

	for (i=0; i<8; i++) {
		if (out->data[i] != answers_2[i]) {
			printf("err (2) %d %f %f\n", i, out->data[i], answers_1[i]);
			fail = 1;
		}
	}
	if (fail)
		return 0;
	return 1;

}

static float sin_coeffs[] = {
0.        ,  1.02723878, -0.11914602, -0.04787508,
-0.12429159,  1.41009724, -0.45090743,  0.00708993,
-0.66900927,  2.35452208, -0.96547636,  0.09130121,
-1.78575778,  3.74577624, -1.53026182,  0.16535537,
-2.8811989 ,  4.7583966 , -1.83407729,  0.19460164,
-2.35376891,  4.09984452, -1.58661354,  0.16535537,
 1.34330369,  1.03527082, -0.755511  ,  0.09130121,
 7.30684176, -3.41647466, 0.317265350, 7.08993236e-03,
 10.12478829, -6.14009133, 1.02156999, -0.04787508 };

int
test_cspline_sin(void)
{
	cspline * c = cspline_new(9, 1024);
	mfp_block * in = mfp_block_new(1024);
	mfp_block * out = mfp_block_new(1024);
	int x;
	int fail = 0;

	cspline_init(c, 0.0, 2.0*M_PI, sin_coeffs);
	for(x = 0; x < 1024; x++) {
		in->data[x] = (float)x * 2.0*M_PI/1024.0;
	}

	cspline_block_eval(c, in, out);

	for(x = 0; x < 1024; x++) {
		if (fabs(out->data[x] - sin(in->data[x])) > 0.01) {
			fail = 1;
			printf("index=%d x=%f expected=%f got=%f\n", x, in->data[x], sin(in->data[x]), out->data[x]); 
		}
	}
	if (fail)
		return 0;
	return 1;
}

static void
naive_block_sin(mfp_block * in, mfp_block * out)
{
	int i;
	for(i=0; i < in->blocksize; i++) {
		out->data[i] = sinf(in->data[i]);
	}
}

int
benchmark_cspline_sin(void) 
{
	struct timeval start, end;
	float naive, fast;
	cspline * c = cspline_new(9, 1024);
	mfp_block * in = mfp_block_new(1024);
	mfp_block * out = mfp_block_new(1024);
	int x;
	int fail = 0;

	cspline_init(c, 0.0, 2.0*M_PI, sin_coeffs);
	for(x = 0; x < 1024; x++) {
		in->data[x] = (float)x * 2.0*M_PI/1024.0;
	}

	gettimeofday(&start, NULL);
	for(x = 0; x < 1024; x++) {
		cspline_block_eval(c, in, out);
	}
	gettimeofday(&end, NULL);
	fast = (end.tv_sec + end.tv_usec/1000000.0) - (start.tv_sec + start.tv_usec / 1000000.0);

	gettimeofday(&start, NULL);
	for(x = 0; x < 1024; x++) {
		naive_block_sin(in, out);
	}
	gettimeofday(&end, NULL);
	naive = (end.tv_sec + end.tv_usec/1000000.0) - (start.tv_sec + start.tv_usec / 1000000.0);

	printf("\n     Naive: %f, fast: %f\n", naive, fast);
	return 1;
}



