/* A disk that loses power: LD_PRELOAD shim for the crash tests.
 *
 * Every write to a file whose path starts with $LOSSY_PREFIX is preceded by an undo record in $LOSSY_LOG
 * (the bytes it is about to overwrite and the file's size); fsync and fdatasync append a "synced" record.
 * After the process is killed, tests/support/lossydisk.py replays the log backwards and undoes every write
 * made since its file's last sync: the state a real disk may be left in by a power cut, with the operating
 * system's page cache gone. A SIGKILL alone cannot show the difference between synchronous=NORMAL and FULL,
 * because the kernel still holds the killed process's writes; this can.
 *
 * Record: type(1) pathlen(u16) path offset(u64) old_size(u64) old_len(u32) old_bytes.   type W write, S sync, T truncate.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define MAXFD 4096
static char *tracked[MAXFD];
static int logfd = -1;
static const char *prefix;
static size_t prefix_len;

#define REAL(ret, name, args) static ret (*real_##name) args
REAL(int, open, (const char *, int, ...));
REAL(int, close, (int));
REAL(ssize_t, write, (int, const void *, size_t));
REAL(ssize_t, pwrite, (int, const void *, size_t, off_t));
REAL(ssize_t, pread, (int, void *, size_t, off_t));
REAL(int, fsync, (int));
REAL(int, fdatasync, (int));
REAL(int, ftruncate, (int, off_t));

static void init(void) {
  if (logfd >= 0) return;
  real_open = dlsym(RTLD_NEXT, "open");
  real_close = dlsym(RTLD_NEXT, "close");
  real_write = dlsym(RTLD_NEXT, "write");
  real_pwrite = dlsym(RTLD_NEXT, "pwrite");
  real_pread = dlsym(RTLD_NEXT, "pread");
  real_fsync = dlsym(RTLD_NEXT, "fsync");
  real_fdatasync = dlsym(RTLD_NEXT, "fdatasync");
  real_ftruncate = dlsym(RTLD_NEXT, "ftruncate");
  prefix = getenv("LOSSY_PREFIX");
  prefix_len = prefix ? strlen(prefix) : 0;
  const char *log = getenv("LOSSY_LOG");
  logfd = log ? real_open(log, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644) : -1;
  if (logfd < 0) logfd = -2;
}

static void record(char type, const char *path, uint64_t off, uint64_t old_size, const void *old, uint32_t old_len) {
  uint16_t plen = (uint16_t)strlen(path);
  size_t total = 1 + 2 + plen + 8 + 8 + 4 + old_len;
  unsigned char *buf = malloc(total), *p = buf;
  *p++ = (unsigned char)type;
  memcpy(p, &plen, 2); p += 2;
  memcpy(p, path, plen); p += plen;
  memcpy(p, &off, 8); p += 8;
  memcpy(p, &old_size, 8); p += 8;
  memcpy(p, &old_len, 4); p += 4;
  if (old_len) memcpy(p, old, old_len);
  real_write(logfd, buf, total);
  free(buf);
}

static int is_tracked_path(const char *path) {
  return prefix_len && strncmp(path, prefix, prefix_len) == 0;
}

static int open_impl(const char *path, int flags, mode_t mode) {
  init();
  int fd = real_open(path, flags, mode);
  if (fd >= 0 && fd < MAXFD && logfd >= 0 && path) {
    char resolved[PATH_MAX];
    const char *use = path;
    if (path[0] != '/' && realpath(path, resolved)) use = resolved;
    if (is_tracked_path(use)) { free(tracked[fd]); tracked[fd] = strdup(use); }
  }
  return fd;
}

int open(const char *path, int flags, ...) {
  mode_t mode = 0;
  if (flags & (O_CREAT | O_TMPFILE)) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  return open_impl(path, flags, mode);
}
int open64(const char *path, int flags, ...) {
  mode_t mode = 0;
  if (flags & (O_CREAT | O_TMPFILE)) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
  return open_impl(path, flags | O_LARGEFILE, mode);
}

int close(int fd) {
  init();
  if (fd >= 0 && fd < MAXFD && tracked[fd]) { free(tracked[fd]); tracked[fd] = NULL; }
  return real_close(fd);
}

static void log_write(int fd, size_t n, off_t off) {
  struct stat st;
  if (fstat(fd, &st) != 0) return;
  uint64_t size = (uint64_t)st.st_size;
  size_t have = (uint64_t)off < size ? (size_t)(size - (uint64_t)off) : 0;
  if (have > n) have = n;
  unsigned char *old = have ? malloc(have) : NULL;
  ssize_t got = have ? real_pread(fd, old, have, off) : 0;
  record('W', tracked[fd], (uint64_t)off, size, old, got > 0 ? (uint32_t)got : 0);
  free(old);
}

ssize_t pwrite(int fd, const void *buf, size_t n, off_t off) {
  init();
  if (fd >= 0 && fd < MAXFD && tracked[fd] && logfd >= 0) log_write(fd, n, off);
  return real_pwrite(fd, buf, n, off);
}
ssize_t pwrite64(int fd, const void *buf, size_t n, off_t off) { return pwrite(fd, buf, n, off); }

ssize_t write(int fd, const void *buf, size_t n) {
  init();
  if (fd >= 0 && fd < MAXFD && tracked[fd] && logfd >= 0) log_write(fd, n, lseek(fd, 0, SEEK_CUR));
  return real_write(fd, buf, n);
}

static int sync_impl(int fd, int (*real)(int)) {
  init();
  int rc = real(fd);
  if (rc == 0 && fd >= 0 && fd < MAXFD && tracked[fd] && logfd >= 0) record('S', tracked[fd], 0, 0, NULL, 0);
  return rc;
}
int fsync(int fd) { init(); return sync_impl(fd, real_fsync); }
int fdatasync(int fd) { init(); return sync_impl(fd, real_fdatasync); }

int ftruncate(int fd, off_t length) {
  init();
  if (fd >= 0 && fd < MAXFD && tracked[fd] && logfd >= 0) {
    struct stat st;
    if (fstat(fd, &st) == 0 && (uint64_t)length < (uint64_t)st.st_size) {
      size_t n = (size_t)(st.st_size - length);
      unsigned char *old = malloc(n);
      ssize_t got = real_pread(fd, old, n, length);
      record('T', tracked[fd], (uint64_t)length, (uint64_t)st.st_size, old, got > 0 ? (uint32_t)got : 0);
      free(old);
    } else if (fstat(fd, &st) == 0) {
      record('T', tracked[fd], (uint64_t)length, (uint64_t)st.st_size, NULL, 0);
    }
  }
  return real_ftruncate(fd, length);
}
int ftruncate64(int fd, off_t length) { return ftruncate(fd, length); }
