#!/usr/bin/env bash
# tools/package.sh - builds the submission archives; both unpack into one folder <name>/:
#
#   dist/<name>_Full_Report.zip     the full report (pdf + docx), all sources and project
#                                   files, the executables, the test examples and the
#                                   unmodified starter code for comparison
#   dist/<name>_Reduced_Report.zip  the reduced report, the sources, the executables, the
#                                   Docker files and the report scripts; no debug/,
#                                   starter_original/, test_examples/, tests/ or tools/
#                                   folder, and no bin/des_test
#
# The executables are taken from the Docker image, where they were compiled on
# Debian 12 (glibc 2.36), so they run on most current Linux distributions and
# not only on the very new one of the development machine.
#
# usage: [REPORT=both|full|reduced] tools/package.sh [name]   (default: both, Lab2_DES)
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:-Lab2_DES}
REPORT=${REPORT:-both}
case "$REPORT" in
    full | reduced) variants=$REPORT ;;
    both)           variants="full reduced" ;;
    *) echo "REPORT must be full, reduced or both" >&2; exit 2 ;;
esac
DIST="$PWD/dist"
mkdir -p "$DIST"
work=$(mktemp -d)                 # the archives are put together here, not in dist/
trap 'rm -rf "$work"' EXIT

docker compose build -q
container=$(docker create des-lab2:latest)
docker cp "$container:/opt/des-lab/bin" "$work/bin"
docker rm "$container" > /dev/null

# README.md of an archive: its first paragraph names only the report in that archive,
# followed by the note $2 (\n for a line break)
readme() {
    awk -v first="The report is \`report/$1.pdf\` (editable: \`.docx\`).$2" '
        /^The report is / { print first; skip = 1; next }
        skip && /^$/      { skip = 0 }
        !skip' README.md
}

package() {    # $1 = full or reduced
    local report zipname stage
    if [ "$1" = full ]; then
        report=DES_Lab2_Report zipname=${NAME}_Full_Report
    else
        report=Reduced_Report zipname=${NAME}_Reduced_Report
    fi
    stage="$work/$1/$NAME"
    mkdir -p "$stage/report"
    cp -r "$work/bin" src docker .vscode "$stage/"
    cp Makefile docker-compose.yml .dockerignore "$stage/"
    cp "report/$report.pdf" "report/$report.docx" report/build_report.py \
       report/build_reduced_report.py report/make_figures.py report/cover.json "$stage/report/"
    cp -r report/assets report/figures "$stage/report/"

    if [ "$1" = full ]; then
        cp -r tests debug tools test_examples "$stage/"
        mkdir "$stage/starter_original"
        cp Lab2_DES/DES_tcp_server_client_program/*.c "$stage/starter_original/"
        readme "$report" "" | sed 's#^| `Lab2_DES/` | the course starter code (unchanged) |#| `starter_original/` | the course starter code (unchanged) |#' \
            > "$stage/README.md"
    else
        rm -f "$stage/bin/des_test"
        # README without what needs the missing folders: their rows of the layout table,
        # bin/des_test, make test/check/demo, the GDB script and "Regenerating the evidence"
        readme "$report" "\n\nThis archive contains the report, the source code, the \
executables and the Docker files. The unit tests, the debugger script, the helper tools, \
the test examples and the original starter code are not included, so \`make test\`, \
\`make check\`, \`make demo\`, \`make examples\`, \`make screenshots\`, \`make report\` \
and \`make dist\` do not work here." |
            sed -e '\#^| `\(tests\|debug\|tools\|test_examples\|Lab2_DES\)/#d' \
                -e 's/^## Build and test (Linux)$/## Build (Linux)/' \
                -e 's# bin/des_test##' \
                -e '/^make \(test\|check\|demo\) /d' \
                -e '/debug\/des_watch\.py/{N;d}' \
                -e '/^## Regenerating the evidence/,$d' > "$stage/README.md"
    fi
    find "$stage" -name '__pycache__' -prune -exec rm -rf {} +

    rm -f "$DIST/$zipname.zip"
    (cd "$work/$1" && zip -qr "$DIST/$zipname.zip" "$NAME")
    echo "dist/$zipname.zip  ($(du -h "$DIST/$zipname.zip" | cut -f1), $(find "$stage" -type f | wc -l) files)"
}

for variant in $variants; do
    package "$variant"
done
