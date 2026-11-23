#!/usr/bin/env bash
# tools/package.sh - builds the submission archive dist/<name>.zip:
#   the report (pdf + docx), all sources and project files, the executables,
#   the test examples and the unmodified starter code for comparison.
#
# The executables are taken from the Docker image, where they were compiled on
# Debian 12 (glibc 2.36), so they run on most current Linux distributions and
# not only on the very new one of the development machine.
#
# usage: [REPORT=full|reduced|both] tools/package.sh [name]   (default: full, Lab2_DES)
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:-Lab2_DES}
REPORT=${REPORT:-full}
case "$REPORT" in
    full)    reports="DES_Lab2_Report" ;;
    reduced) reports="Reduced_Report" ;;
    both)    reports="DES_Lab2_Report Reduced_Report" ;;
    *) echo "REPORT must be full, reduced or both" >&2; exit 2 ;;
esac
STAGE="dist/$NAME"
rm -rf "$STAGE" "dist/$NAME.zip"
mkdir -p "$STAGE/report" "$STAGE/starter_original"

docker compose build -q
container=$(docker create des-lab2:latest)
docker cp "$container:/opt/des-lab/bin" "$STAGE/bin"
docker rm "$container" > /dev/null

cp -r src tests debug docker tools test_examples .vscode "$STAGE/"
cp Makefile README.md docker-compose.yml .dockerignore "$STAGE/"
for r in $reports; do
    cp "report/$r.pdf" "report/$r.docx" "$STAGE/report/"
done
cp report/build_report.py report/build_reduced_report.py report/make_figures.py \
   report/cover.json "$STAGE/report/"
cp -r report/assets "$STAGE/report/"
cp -r report/figures "$STAGE/report/"
cp Lab2_DES/DES_tcp_server_client_program/*.c "$STAGE/starter_original/"
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +
sed -i 's#^| `Lab2_DES/` | the course starter code (unchanged) |#| `starter_original/` | the course starter code (unchanged) |#' \
    "$STAGE/README.md"

(cd dist && zip -qr "$NAME.zip" "$NAME")
echo "dist/$NAME.zip  (report: $REPORT, $(du -h "dist/$NAME.zip" | cut -f1), $(find "$STAGE" -type f | wc -l) files)"
