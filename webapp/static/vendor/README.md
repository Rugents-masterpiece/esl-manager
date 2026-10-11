# Offline code encoders

Runtime reads only same-origin local scripts. No CDN lookup is performed by the editor.

- JsBarcode 3.11.6, Code128 browser bundle, MIT. Upstream: https://github.com/lindell/JsBarcode. Exact bundle source: https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/barcodes/JsBarcode.code128.min.js. Copyright and full permission notice: JsBarcode.LICENSE (from the matching npm package's MIT-LICENSE.txt).
- qrcode-generator 1.4.4, MIT. Upstream: https://github.com/kazuhikoarase/qrcode-generator. Exact sources: https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.js and https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode_UTF8.js. Full permission notice: qrcode.LICENSE (upstream repository LICENSE; copyright agrees with the preserved 1.4.4 source header). The UTF-8 add-on is required for Slovak text and emoji.

ASSET-MANIFEST.json records original download URLs, actual lengths and SHA-256 hashes. Preserve these scripts as downloaded, including their headers. First guessed JsBarcode path outside dist/barcodes returned HTTP 404; the successful artifact is the dist/barcodes file listed above.

SVG layout, native-resolution integer module sizing, quiet zones, local image processing and the editor integration are application code, not modifications to these upstream bundles. Barcode rendering currently supports Code128 only; it does not claim EAN/UPC or vendor publication compatibility.
