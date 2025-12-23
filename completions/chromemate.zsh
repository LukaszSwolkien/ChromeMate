#compdef chromemate

# Static completion for chromemate (works with PyInstaller binary)

_chromemate() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '--help[Show help message]' \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            local commands=(
                'profiles:List all available Chrome profiles'
                'analyze:Analyze a Chrome profile and show usage report'
                'export:Export profile data for migration'
                'merge-history:Merge browsing history from one profile into another'
            )
            _describe 'command' commands
            ;;
        args)
            case $line[1] in
                profiles)
                    _arguments '--help[Show help]'
                    ;;
                analyze)
                    _arguments \
                        '(-p --profile)'{-p,--profile}'[Profile name]:profile:' \
                        '(-t --top)'{-t,--top}'[Limit results]:count:' \
                        '(-i --include)'{-i,--include}'[Include URLs matching pattern]:pattern:' \
                        '(-x --exclude)'{-x,--exclude}'[Exclude URLs matching pattern]:pattern:' \
                        '(-B --bookmarked-only)'{-B,--bookmarked-only}'[Only bookmarked sites]' \
                        '(-U --unused)'{-U,--unused}'[Show unvisited bookmarks]' \
                        '(-a --aggregate)'{-a,--aggregate}'[Aggregate by url or domain]:mode:(url domain)' \
                        '--aggregate-url[Aggregate by URL for matching domains]:pattern:' \
                        '--aggregate-domain[Aggregate by domain for matching domains]:pattern:' \
                        '(-d --days)'{-d,--days}'[History from last N days]:days:' \
                        '--help[Show help]'
                    ;;
                export)
                    _arguments \
                        '(-p --profile)'{-p,--profile}'[Profile name]:profile:' \
                        '(-o --output)'{-o,--output}'[Output directory]:directory:_files -/' \
                        '(-b --bookmarks)'{-b,--bookmarks}'[Export bookmarks]' \
                        '(-e --extensions)'{-e,--extensions}'[Export extensions]' \
                        '--history[Export browsing history]' \
                        '(-t --top)'{-t,--top}'[Limit results]:count:' \
                        '(-i --include)'{-i,--include}'[Include URLs matching pattern]:pattern:' \
                        '(-x --exclude)'{-x,--exclude}'[Exclude URLs matching pattern]:pattern:' \
                        '(-B --bookmarked-only)'{-B,--bookmarked-only}'[Only bookmarked sites]' \
                        '(-U --unused)'{-U,--unused}'[Export unvisited bookmarks]' \
                        '(-a --aggregate)'{-a,--aggregate}'[Aggregate by url or domain]:mode:(url domain)' \
                        '--aggregate-url[Aggregate by URL for matching domains]:pattern:' \
                        '--aggregate-domain[Aggregate by domain for matching domains]:pattern:' \
                        '(-d --days)'{-d,--days}'[History from last N days]:days:' \
                        '--include-unvisited[Include unvisited bookmarks matching pattern]:pattern:' \
                        '(-c --count)'{-c,--count}'[Preview count without exporting]' \
                        '--help[Show help]'
                    ;;
                merge-history)
                    _arguments \
                        '1:source profile:' \
                        '2:target profile:' \
                        '(-n --dry-run)'{-n,--dry-run}'[Preview without modifying]' \
                        '(-y --yes)'{-y,--yes}'[Skip confirmation]' \
                        '--help[Show help]'
                    ;;
            esac
            ;;
    esac
}

_chromemate "$@"
