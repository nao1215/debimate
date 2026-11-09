#!/bin/sh
# 使い方: sh build.sh <段階 0〜5>
# project/ を取り出して tar.gz を作り、標準出力に書きます。
set -eu
stage=$1

# ソースの取り出し（git clone の代わり）。中身は毎回同じです。
rm -rf project
mkdir -p project/docs
printf 'hello\n' > project/README
printf 'usage\n' > project/docs/usage.txt
printf '#!/bin/sh\necho hello\n' > project/hello.sh
chmod +x project/hello.sh

t="--mtime=@${SOURCE_DATE_EPOCH}"
o="--owner=0 --group=0 --numeric-owner"
m="--mode=a=rX,u+w"
case "$stage" in
  0) tar -cf project.tar project ;;
  1) tar -cf project.tar project ;;
  2) tar "$t" -cf project.tar project ;;
  3) tar --sort=name "$t" -cf project.tar project ;;
  4) tar --sort=name "$t" $o -cf project.tar project ;;
  5) tar --sort=name "$t" $o "$m" -cf project.tar project ;;
esac
if [ "$stage" = 0 ]; then
  gzip -c project.tar      # gzip ヘッダーにファイル名と mtime が入る
else
  gzip -n -c project.tar   # -n: ファイル名と mtime を入れない
fi
