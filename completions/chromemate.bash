# Bash completion for chromemate (works with PyInstaller binary)

_chromemate() {
    local cur prev words cword
    _init_completion || return

    local commands="profiles analyze export merge-history"
    
    local analyze_opts="--profile -p --top -t --include -i --exclude -x --bookmarked-only -B --unused -U --aggregate -a --aggregate-url --aggregate-domain --days -d --help"
    
    local export_opts="--profile -p --output -o --bookmarks -b --extensions -e --history --top -t --include -i --exclude -x --bookmarked-only -B --unused -U --aggregate -a --aggregate-url --aggregate-domain --days -d --include-unvisited --count -c --help"
    
    local merge_opts="--dry-run -n --yes -y --help"

    case $cword in
        1)
            COMPREPLY=($(compgen -W "$commands --help" -- "$cur"))
            ;;
        *)
            case ${words[1]} in
                profiles)
                    COMPREPLY=($(compgen -W "--help" -- "$cur"))
                    ;;
                analyze)
                    COMPREPLY=($(compgen -W "$analyze_opts" -- "$cur"))
                    ;;
                export)
                    case $prev in
                        -o|--output)
                            _filedir -d
                            ;;
                        -a|--aggregate)
                            COMPREPLY=($(compgen -W "url domain" -- "$cur"))
                            ;;
                        *)
                            COMPREPLY=($(compgen -W "$export_opts" -- "$cur"))
                            ;;
                    esac
                    ;;
                merge-history)
                    COMPREPLY=($(compgen -W "$merge_opts" -- "$cur"))
                    ;;
            esac
            ;;
    esac
}

complete -F _chromemate chromemate

