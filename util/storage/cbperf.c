/*
 *  Copyright 2012 Cachebox, Inc. All rights reserved. This software
 *  is property of Cachebox, Inc and contains trade secrets,
 *  confidential & proprietary information. Use, disclosure or copying
 *  this without explicit written permission from Cachebox, Inc is
 *  prohibited.
 *
 *  Author: Cachebox, Inc (sales@cachebox.com)
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <inttypes.h>
#include <getopt.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/fs.h>


#define	MAX_STR_SIZE	256
#define MEMALIGN_SIZE	4096
#define SECTOR_SIZE	512

//Error codes
#define	INVAL_ARG	1
#define MEM_FAILED	2
#define	OPEN_FAILED	3
#define SIZE_FAILED	4
#define THREAD_FAILED	5

#define SEC2NSECS(x)	((x) << 30)

typedef unsigned long	ulong64_t;

//Thread structure holds paramaters for each thread
typedef struct thread_param {
	char		*al_buffer;	//memaligned buffer for I/O
	char		*ul_buffer;	//unaligned buffer
	pthread_t	id;	
} thread_param_t;

//Arguments for easy sharing across functions
struct args {
	int		blocksize;  //blocksize for I/O
	char		device[MAX_STR_SIZE];
	int		qdepth;
	long		timeout;
	int		fd;
	ulong64_t	devsize;
	thread_param_t	*threads;   //threads array
	int		thcount;            //thread count
	int		iostart;
	int		iostop;
	pthread_mutex_t iomutex;
	pthread_cond_t  iosignal;
	int		iocount;
} args;

char *command = "cbperf";

void
usage(void)
{
	fprintf(stderr, "%s <device> -b <blocksize> -q <qdepth> -t <time(secs)>\n", command);
	exit(INVAL_ARG);
}

ulong64_t
random_number(ulong64_t max)
{
	return ((ulong64_t)rand() | ((ulong64_t)rand() << 32)) % max;
}

//Generate next offset for I/O, aligned to blocksize boundary
ulong64_t
get_nextoffset(void)
{
	ulong64_t	nextoff;

	nextoff = random_number(args.devsize);
	nextoff = nextoff & ~(args.blocksize - 1);

	return nextoff;
}

ulong64_t
now(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_REALTIME, &ts);

	return SEC2NSECS(ts.tv_sec) + ts.tv_nsec;
}

int
atomic_inc(int *val)
{
	return __sync_add_and_fetch(val, 1);
}

int
atomic_dec(int *val)
{
	return __sync_add_and_fetch(val, -1);
}


/*
 * Main function for doing I/Os.
 * Each pthread runs this function.
 * Once the start I/O signal is got,
 * each thread generate independent random offsets
 * and issue read I/Os, till the stop signal is received 
 */
int
do_io(void *context)
{
	int		res = 0;
	ulong64_t	offset = 0;
	thread_param_t	*thread = (thread_param_t *)context;

	pthread_mutex_lock(&args.iomutex);
	if (!args.iostart) {
		pthread_cond_wait(&args.iosignal, &args.iomutex);
	}
	pthread_mutex_unlock(&args.iomutex);

	while (!args.iostop) {
		offset = get_nextoffset();
			
                if (pread(args.fd, thread->al_buffer, args.blocksize, offset) != args.blocksize) {
                        res = errno;
                        fprintf(stderr, "read at %lu failed: 0x%x\n", offset, res);
                        return res;
                }

		atomic_inc(&args.iocount);
	}

	return 0;
}

ulong64_t
get_devsize(int fd)
{
        ulong64_t       devsize = 0;
        int             ret = 0;

        ret = ioctl(fd, BLKGETSIZE64, &devsize);

        if (ret) {
                fprintf(stderr, "Failed to get the device size: 0x%x\n", errno);
                return -1;
        }

        return devsize;
}

/*
 * Returns the buffer useful for doing direct I/Os. 
 * Also returns the original unaligned buffer, so that
 * it can be freed at the end.
 */
int
memaligned_buffer(char **aligned_buf, char **unaligned_buf, int size)
{
        *unaligned_buf = malloc(size + MEMALIGN_SIZE);
        if (!*unaligned_buf) {
		fprintf(stderr, "Memory allocation failed for buffer: %d\n", size);
                return MEM_FAILED;
	}
        *aligned_buf = *unaligned_buf + MEMALIGN_SIZE - (size_t)*unaligned_buf % MEMALIGN_SIZE;

	return 0;
}

void
thread_cleanup(void)
{
        int i;

	args.iostop = 1;
        for (i = 0; i < args.thcount; i++) {
                pthread_join(args.threads[i].id, NULL);
                free(args.threads[i].ul_buffer);
        }
        free(args.threads);

        args.threads = NULL;
        args.thcount = 0;
}

int
thread_alloc(void)
{
	int	i;
	int	ret;

        args.threads = calloc(sizeof(thread_param_t), args.qdepth);
        if (args.threads == NULL) {
                fprintf(stderr, "Pthread allocation failed\n");
                return MEM_FAILED;
        }

        for (i = 0; i < args.qdepth; i++) {

		thread_param_t *thread = &args.threads[i];

		if (memaligned_buffer(&thread->al_buffer, &thread->ul_buffer, args.blocksize)) {
			ret = MEM_FAILED;
			goto err_out;
		}
		if (pthread_create(&thread->id, NULL, do_io, thread)) {
			fprintf(stderr, "Pthread creation failed: 0x%x\n", ret);
			ret = THREAD_FAILED;
			goto err_out;
		}
		args.thcount++;
	}

	return 0;

err_out:

	thread_cleanup();

	return ret;
}

void
perf_init(void)
{
	args.blocksize	= 4096;
	args.qdepth	= 1;
	args.timeout	= 10;
}

int
perf_parse(int argc, char *argv[])
{
	int	opt;

	if (argc < 2) {
		usage();
	}

	strcpy(args.device, argv[1]);

	optind += 1;

	while ((opt = getopt_long(argc, argv, "b:q:t:", NULL, NULL)) != -1) {
		switch (opt) {
			case 'b':
				args.blocksize = atoi(optarg);
				break;

			case 'q':
				args.qdepth = atoi(optarg);
				break;

			case 't':
				args.timeout = atol(optarg);
				break;

			default:
				usage();
				break;
		}
	}

	return 0;
}

int
perf_prerun(void)
{
	int		i;
	int		res;

	if (args.timeout <= 0) {
		fprintf(stderr, "Invalid time specified\n");
		return INVAL_ARG;
	}

	if ((args.blocksize <= 0) || (args.blocksize % SECTOR_SIZE)) {
		fprintf(stderr, "Blocksize must be multiple of %d\n", SECTOR_SIZE);
		return INVAL_ARG;
	}

	if (strcmp(args.device, "") == 0) {
		fprintf(stderr, "Device name must be provided\n");
		return INVAL_ARG;
	}

	args.fd = open(args.device, O_RDONLY | O_DIRECT);
	if (args.fd < 0) {
		fprintf(stderr, "Device %s open failed: 0x%x\n", args.device, errno);
		return OPEN_FAILED;
	}

	args.devsize = get_devsize(args.fd);
	if (args.devsize < 0) {
		fprintf(stderr, "Device size get failed\n");
		return SIZE_FAILED;
	}

	pthread_mutex_init(&args.iomutex, NULL);
	pthread_cond_init(&args.iosignal, NULL);

	res = thread_alloc();

	srandom(now());

	return res;
}

void
print_report(void)
{
	printf("iops=%lu\n", args.iocount/args.timeout);
}

int
perf_run(void)
{
	int	i;

	pthread_mutex_lock(&args.iomutex);
	args.iostart = 1;
	pthread_cond_broadcast(&args.iosignal);
	pthread_mutex_unlock(&args.iomutex);

	sleep(args.timeout);

	args.iostop = 1;
	
	thread_cleanup();	

	print_report();

	return 0;
}

void
perf_uninit(void)
{
	int	i;

	if (args.fd) {
		close(args.fd);
	}

	pthread_mutex_lock(&args.iomutex);
	args.iostart = 1;
	pthread_cond_broadcast(&args.iosignal);
	pthread_mutex_unlock(&args.iomutex);
	
	thread_cleanup();

	pthread_cond_destroy(&args.iosignal);
}

int
main(int argc, char *argv[])
{
	int	ret;

	perf_init();

	ret = perf_parse(argc, argv);
	if (ret) {
		return ret;
	}

	ret = perf_prerun();
	if (!ret) {
		ret = perf_run();	
	}

out:

	perf_uninit();

	return ret;
}
