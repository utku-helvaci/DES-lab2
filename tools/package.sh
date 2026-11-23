#!/usr/bin/env bash
# tools/package.sh - builds the submission archives; both unpack into one folder <name>/:
#
#   dist/<name>_Full_Report.zip     the full report (pdf + docx) and the scripts that build
#                                   it, all sources and project files, the executables, the
#                                   test examples and the unmodified starter code
#   dist/<name>_Reduced_Report.zip  the reduced report (pdf + docx only), the sources, the
#                                   executables and the Docker files; no debug/,
#                                   starter_original/, test_examples/, tests/ or tools/, no
#                                   report scripts, screenshots or bin/des_test. Its README
#                                   has only the title and the sections "Run on two machines
#                                   (Docker)", "DES step tables" and "Debugging".
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

# README.md of the full archive: the first paragraph names only the full report
readme_full() {
    awk '/^The report is / { print "The report is `report/DES_Lab2_Report.pdf` (editable: `.docx`)."
                             skip = 1; next }
         skip && /^$/      { skip = 0 }
         !skip' README.md |
        sed 's#^| `Lab2_DES/` | the course starter code (unchanged) |#| `starter_original/` | the course starter code (unchanged) |#'
}

# README.md of the reduced archive: the title and three sections, without the lines that
# need a folder it leaves out (make demo, the GDB script in debug/)
readme_reduced() {
    awk -v sections="Run on two machines (Docker)|DES step tables|Debugging" '
        BEGIN    { n = split(sections, s, "|"); for (i = 1; i <= n; i++) want["## " s[i]] }
        NR == 1  { print; blank = 1; next }                      # the title
        /^## /   { keep = ($0 in want); if (keep) seen[$0] }
        !keep    { next }
        /^$/     { blank++; next }                               # no blank line at the end
                 { for (; blank > 0; blank--) print ""; print }
        END      { for (h in want) if (!(h in seen)) {
                       print "README.md has no section \"" h "\"" > "/dev/stderr"; exit 1 } }
    ' README.md |
        sed -e '/^make demo /d' -e '/debug\/des_watch\.py/{N;d}'
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
    cp "report/$report.pdf" "report/$report.docx" "$stage/report/"

    if [ "$1" = full ]; then
        cp report/build_report.py report/build_reduced_report.py report/make_figures.py \
           report/cover.json "$stage/report/"
        cp -r report/assets report/figures "$stage/report/"
        cp -r tests debug tools test_examples "$stage/"
        mkdir "$stage/starter_original"
        cp Lab2_DES/DES_tcp_server_client_program/*.c "$stage/starter_original/"
        readme_full > "$stage/README.md"
    else
        rm -f "$stage/bin/des_test"
        readme_reduced > "$stage/README.md"
    fi
    find "$stage" -name '__pycache__' -prune -exec rm -rf {} +

    rm -f "$DIST/$zipname.zip"
    (cd "$work/$1" && zip -qr "$DIST/$zipname.zip" "$NAME")
    echo "dist/$zipname.zip  ($(du -h "$DIST/$zipname.zip" | cut -f1), $(find "$stage" -type f | wc -l) files)"
}

for variant in $variants; do
    package "$variant"
done
