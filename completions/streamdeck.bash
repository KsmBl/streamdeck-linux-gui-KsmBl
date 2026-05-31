# Bash completion for the `streamdeck` command.
# Installed by scripts/install.sh.

_streamdeck() {
    local cur opts
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="-h --help -n --no-ui -d --daemon --daemon-kill --daemon-status"
    COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
}
complete -F _streamdeck streamdeck
