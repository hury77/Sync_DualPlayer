#import <Cocoa/Cocoa.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <signal.h>

pid_t child_pid = 0;

@interface AppDelegate : NSObject <NSApplicationDelegate>
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
    char path[2048];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) == 0) {
        char *dir = dirname(path);
        char script_path[4096];
        snprintf(script_path, sizeof(script_path), "%s/Sync_DualPlayer_run.sh", dir);
        
        child_pid = fork();
        if (child_pid == 0) {
            // W procesie potomnym tworzymy nową grupę procesów,
            // aby potem móc ubić skrypt i wszystkie jego dzieci (np. uvicorn, ffmpeg).
            setpgid(0, 0);
            execl("/bin/bash", "bash", script_path, (char *)NULL);
            exit(1);
        }
    }
}

- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    if (child_pid > 0) {
        // Wysyłamy SIGTERM do całej grupy procesów
        kill(-child_pid, SIGTERM);
    }
    return NSTerminateNow;
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        
        // Tryb aplikacji z ikonką w docku (Regular).
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        
        [app run];
    }
    return 0;
}
