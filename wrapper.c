#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <libgen.h>
#include <mach-o/dyld.h>

int main(int argc, char *argv[]) {
    char path[2048];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) == 0) {
        char *dir = dirname(path);
        char script_path[4096];
        snprintf(script_path, sizeof(script_path), "%s/Sync_DualPlayer_run.sh", dir);
        execl("/bin/bash", "bash", script_path, (char *)NULL);
    }
    return 1;
}
