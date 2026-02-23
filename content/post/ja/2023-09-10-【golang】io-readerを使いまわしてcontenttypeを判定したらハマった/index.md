---
title: "【golang】io.Readerを使いまわしてContentType判定、S3アップロードしたらハマった話"
type: post
date: 2023-09-10
categories:
  - "linux"
tags:
  - "golang"
  - "linux"
cover:
  image: "images/boys-3396713_640.jpg"
  alt: "【golang】io.Readerを使いまわしてContentType判定、S3アップロードしたらハマった話"
  hidden: false
---

### 前書き：同じハマりを繰り返す

Single Page Application（SPA）をAmazon S3にアップロードする機能を持つ[spareコマンド](https://github.com/nao1215/spare)を開発しているとき、io.Readerの使い方を間違えて少しハマってしまいました。ハマりの原因はio.Readerで読み出すデータが欠損していたことであり、欠損の原因はio.Readerを使いまわしたことです。

このハマり方は2回目なので、備忘録として記事にします。

---


### ことの発端（時系列）

1. spareコマンドにファイルをS3へアップロードする機能を追加し、S3にSPAをアップロード
2. CloudFront経由でS3に格納されているindex.htmlをチェックしたら、画面には何も表示されず、ダウンロード処理が開始された
3. 上記2.の挙動となった理由は、ファイルをS3へアップロードする時にContentTypeを指定していなかったため
4. [httpパッケージのDetectContentType](https://pkg.go.dev/net/http#DetectContentType)メソッドでファイルのコンテンツタイプを判定し、その情報をS3へのアップロード時に付与する実装に変更
5. SPAをS3へアップロードし直し
6. 再度CloudFront経由でindex.htmlをチェックしたら、ダウンロード処理が開始されなくなったが、ブラウザには何も表示されなかった　

---


### どこが駄目だったか

以下のUploadFileメソッドは、引数input.Dataを持っており、この引数がio.Readerです。

input.Data は、detectContentType() と s3manager.UploadInput() に渡されています。

detectContentType()は、io.Readerから512バイト読み込み、読み込んだデータからコンテンツタイプを判定します。

s3manager.UploadInput()は、渡されたio.Readerからデータを読み込み、S3へアップロードします

```
func (s *S3Uploader) UploadFile(_ context.Context, input *service.FileUploaderInput) (*service.FileUploaderOutput, error) {
	contentType, err := detectContentType(input.Data)
	if err != nil {
		return nil, errfmt.Wrap(service.ErrFileUpload, err.Error())
	}

	uploadInput := &s3manager.UploadInput{
		Bucket:      aws.String(input.BucketName.String()),
		Body:        aws.ReadSeekCloser(input.Data),
		Key:         aws.String(input.Key),
		ContentType: aws.String(contentType),
	}

	if _, err := s.Upload(uploadInput); err != nil {
		return nil, err
	}
	return &service.FileUploaderOutput{
		DetectedMIMEType: contentType,
	}, nil
}

func detectContentType(reader io.Reader) (string, error) {
	buffer := make([]byte, 512)
	_, err := reader.Read(buffer)
	if err != nil && err != io.EOF {
		return "", errfmt.Wrap(service.ErrNotDetectContentType, err.Error())
	}
	return http.DetectContentType(buffer), nil
}           

```

このinput.Dataの使い回しが原因で、ブラウザでindex.htmlを確認する時に何も表示されませんでした。

---


### 何が悪いか：io.Readerは読込毎に読込開始位置が進む

私は古い人間なので、「io.Readerは、C言語のファイルポインタと一緒か」とすぐ思いました。

io.Readerはデータの読み込み処理を実行すると、ファイルの読み込み開始位置が進みます。そのため、先程の例では「コンテンツタイプを読み込むために512Byte分、読み込み開始位置が移動」「S3へのアップロード時は、ファイルの先頭から512Byte進んだ地点のデータからファイル終端までをアップロード」という挙動をしていたことになります。

---


### 解決策１：io.ReadSeekerなどのio.Seekerインターフェースを利用

先程の例のinput.Data（io.Reader）が[io.Seeker](https://pkg.go.dev/io#Seeker)を満たす場合は、input.Dataの型をio.ReadSeekerに変更するのが簡単です。ファイルの読み出し位置を変えるには、以下の例のようにSeek()メソッドを用います。

```
package main

import (
	"fmt"
	"io"
	"os"
)

func main() {
	// ファイルをオープンして読み込み可能なio.ReadSeekerを作成します
	file, err := os.Open("example.txt")
	if err != nil {
		fmt.Println("ファイルを開けませんでした:", err)
		return
	}
	defer file.Close()

	// ファイルの内容を読み取ります
	data := make([]byte, 20)
	n, err := file.Read(data)
	if err != nil {
		fmt.Println("読み込みエラー:", err)
		return
	}
	fmt.Printf("最初の %d バイトを読み取りました: %s\n", n, data[:n])

	// ファイルの開始位置を戻します
	_, err = file.Seek(0, io.SeekStart)
	if err != nil {
		fmt.Println("Seekエラー:", err)
		return
	}

	// ファイルの内容をもう一度読み取ります
	n, err = file.Read(data)
	if err != nil {
		fmt.Println("読み込みエラー:", err)
		return
	}
	fmt.Printf("再度最初の %d バイトを読み取りました: %s\n", n, data[:n])
}

```

---


### 解決策2：io.Readerを複製

io.Readerがio.Seekerインターフェースを満たしていない場合はどうでしょうか。この場合は、io.Readerを複製する方法が考えられます。

例えば、[io.ReadAll()](https://pkg.go.dev/io#Seeker)でデータをバイトスライスとして読み込み、バイトスライスから２つのio.Readerを作ることができます。ただし、この方法はio.Readerで読み込むデータのサイズが大きい場合、データ読み込みに時間がかかり処理が遅くなる点に注意してください。

```
func duplicateReader(r io.Reader) (io.Reader, io.Reader, error) {
	data, err := io.ReadAll(r)
	if err != nil {
		return nil, nil, err
	}
	return bytes.NewReader(data), bytes.NewReader(data), nil
}

```

実行時間を気にする場合は、[io.TeeReader()](https://pkg.go.dev/io#TeeReader)を使う案が考えられます。io.TeeReader()は、データを読み取りながら、同時にそのデータを別の場所にコピーできます。そのため、io.Readerからデータを読み取りつつ、同じデータをバッファに書き込むことができます。

```
package main

import (
	"fmt"
	"io"
	"strings"
)

func main() {
	input := "Hello, World!"
	reader := strings.NewReader(input)

	// データを複製するためのバッファを作成します
	var buffer1, buffer2 strings.Builder

	// TeeReaderを作成し、データを複製します
	teeReader := io.TeeReader(reader, &buffer1)

	// データを読み取りながら標準出力にコピーします
	_, err := io.Copy(&buffer2, teeReader)
	if err != nil {
		fmt.Println("コピー中にエラーが発生しました:", err)
		return
	}

	fmt.Println("元のデータ:", input)
	fmt.Println("バッファ1にコピーされたデータ:", buffer1.String())
	fmt.Println("バッファ2にコピーされたデータ:", buffer2.String())
}

```

---


### 最後に：CSSとJSのコンテンツ判定方法が分からない

本記事で登場したhttp.DetectContentType()は、コンテンツがCSSかJavaScriptかを判定しません。そのため、CloudFrontからindex.htmlを確認した時に、表示が崩れる問題が発生しました。表示崩れの原因は、コンテンツタイプを正しく指定せずにS3へファイルをアップロードしたからです。

より細かくコンテンツタイプを判定できる[gabriel-vasile/mimetype](https://github.com/gabriel-vasile/mimetype)を利用しましたが、こちらもCSSとJavaScriptを正しく判定できないようでした。そのため、以下の実装のように拡張子で判定する処理を暫定的に入れてます。

```
func detectContentType(reader io.Reader, filename string) (string, error) {
	var extensionToContentType = map[string]string{
		".css": "text/css",
		".js":  "application/javascript",
	}
	contentType, found := extensionToContentType[filepath.Ext(filename)]
	if found {
		return contentType, nil
	}

	mtype, err := mimetype.DetectReader(reader)
	if err != nil {
		return "", errfmt.Wrap(service.ErrNotDetectContentType, err.Error())
	}
	return mtype.String(), nil
}

```

この方法は好ましくないので、上手な判定方法を見つけないとなと思ってます（が、他に優先する事項があるので、放置しています）
