# Fish shell completions for the `streamdeck` command.
# Installed by scripts/install.sh.

# The command takes no file arguments.
complete -c streamdeck -f

complete -c streamdeck -s h -l help        -d 'Show help and exit'
complete -c streamdeck -s n -l no-ui       -d 'Run without showing the configuration window'
complete -c streamdeck -s d -l daemon        -d 'Run detached in the background (implies --no-ui)'
complete -c streamdeck      -l daemon-kill   -d 'Stop the running background instance and exit'
complete -c streamdeck      -l daemon-status -d 'Report whether an instance is running and exit'
