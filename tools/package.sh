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
#                                   (Docker)", "DES step tables" and "Debugging"; its
#                                   Makefile has only the targets all, demo and clean.
#   dist/<name>_3rdtimesthecharm.zip  the document with one C file (pdf + docx), lab2.c, its
#                                   executable and the Docker files. Only made when asked
#                                   for: REPORT=3rdtimesthecharm
#
# The executables are taken from the Docker image, where they were compiled on
# Debian 12 (glibc 2.36), so they run on most current Linux distributions and
# not only on the very new one of the development machine.
#
# usage: [REPORT=both|full|reduced|3rdtimesthecharm] tools/package.sh [name]
#        (default: both, Lab2_DES)
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:-Lab2_DES}
REPORT=${REPORT:-both}
case "$REPORT" in
    full | reduced | 3rdtimesthecharm) variants=$REPORT ;;
    both)                              variants="full reduced" ;;
    *) echo "REPORT must be full, reduced, both or 3rdtimesthecharm" >&2; exit 2 ;;
esac
DIST="$PWD/dist"
mkdir -p "$DIST"
work=$(mktemp -d)                 # the archives are put together here, not in dist/
trap 'rm -rf "$work"' EXIT

# copy_from_image <image> <path in the image> <destination>
copy_from_image() {
    local container
    container=$(docker create "$1")
    docker cp -q "$container:$2" "$3"
    docker rm "$container" > /dev/null
}

if [ "$REPORT" != 3rdtimesthecharm ]; then
    docker compose build -q
    copy_from_image des-lab2:latest /opt/des-lab/bin "$work/bin"
fi

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

# Makefile of the reduced archive: without the targets that test the programs or make the
# examples, screenshots, reports and zips, and without what only those targets use (their
# help lines, REPORT, bin/des_test)
makefile_reduced() {
    local targets='test crosscheck loopback check examples screenshots figures'
    targets+=' report full-report reduced-report dist $(BIN)/des_test'
    awk -v targets="$targets" '
        BEGIN { n = split(targets, t, " "); for (i = 1; i <= n; i++) drop[t[i]]
                RS = ""; FS = "\n" }                      # one paragraph at a time
        {   for (i = 1; i < NF && $i ~ /^#/; i++);        # a rule stands below its comment
            rule = $i; sub(/:.*/, "", rule)
            if (rule in drop) { seen[rule]; next }
            if (NR > 1) print "" }
        rule == ".PHONY" {
            gsub(/\\\n/, ""); n = split($0, word, " "); line = word[1]
            for (i = 2; i <= n; i++) if (!(word[i] in drop)) line = line " " word[i]
            print line; next }
        {   skip = 0                                      # help lines: "#   make <target>"
            for (i = 1; i <= NF; i++) {
                if ($i ~ /^#   make/)    { split($i, word, " "); skip = (word[3] in drop) }
                else if ($i !~ /^#    /) skip = 0
                if (!skip) print $i } }
        END { for (r in drop) if (!(r in seen)) {
                  print "Makefile has no target \"" r "\"" > "/dev/stderr"; exit 1 } }
    ' Makefile |
        sed -e '/^# zip(s) made by/,/^REPORT /d' \
            -e '/^# the zip of the reduced report/,/^PROGRAMS += /d'
}

make_zip() {   # $1 = folder that contains $NAME/, $2 = name of the zip
    rm -f "$DIST/$2.zip"
    (cd "$1" && zip -qr "$DIST/$2.zip" "$NAME")
    echo "dist/$2.zip  ($(du -h "$DIST/$2.zip" | cut -f1), $(find "$1/$NAME" -type f | wc -l) files)"
}

package_3rdtimesthecharm() {
    local src=3rdtimesthecharm stage="$work/3rdtimesthecharm/$NAME" image
    mkdir -p "$stage/report"
    cp "$src/lab2.c" "$src/Dockerfile" "$src/docker-compose.yml" "$src/README.md" "$stage/"
    cp report/3rdtimesthecharm.pdf report/3rdtimesthecharm.docx "$stage/report/"
    image=$(docker build -q "$src")
    copy_from_image "$image" /lab2/lab2 "$stage/lab2"
    make_zip "$work/3rdtimesthecharm" "${NAME}_3rdtimesthecharm"
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
    cp docker-compose.yml .dockerignore "$stage/"
    cp "report/$report.pdf" "report/$report.docx" "$stage/report/"

    if [ "$1" = full ]; then
        cp report/build_report.py report/build_reduced_report.py report/make_figures.py \
           report/cover.json "$stage/report/"
        cp -r report/assets report/figures "$stage/report/"
        cp -r tests debug tools test_examples "$stage/"
        mkdir "$stage/starter_original"
        cp Lab2_DES/DES_tcp_server_client_program/*.c "$stage/starter_original/"
        cp Makefile "$stage/"
        readme_full > "$stage/README.md"
    else
        rm -f "$stage/bin/des_test"
        makefile_reduced > "$stage/Makefile"
        readme_reduced > "$stage/README.md"
    fi
    find "$stage" -name '__pycache__' -prune -exec rm -rf {} +

    make_zip "$work/$1" "$zipname"
}

for variant in $variants; do
    if [ "$variant" = 3rdtimesthecharm ]; then
        package_3rdtimesthecharm
    else
        package "$variant"
    fi
done
