# utils/ocr_utils.py
import os
import shutil
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import numpy as np
from pathlib import Path

def extract_text_from_file(file_location, output_folder):
    dpi = 300
    lang = "chi_tra+eng"
    file_extension = os.path.splitext(file_location)[1]
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    all_text = []

    if file_extension.lower() == '.pdf':
        images = convert_from_path(
            file_location,
            dpi=dpi,
            fmt="jpeg",
            output_folder=output_folder,
            thread_count=4
        )

        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang=lang, config="--psm 6 --oem 3")
            all_text.append(text)

            page_output = os.path.join(output_folder, f"page_{i+1}.txt")
            with open(page_output, "w", encoding="utf-8") as f:
                f.write(text)
                print(f"Page {i+1} OCR 完成，保存至 {page_output}")

    elif file_extension.lower() in image_extensions:
        img = Image.open(file_location)
        img_np = np.array(img)
        text = pytesseract.image_to_string(img_np, lang=lang, config="--psm 6 --oem 3")
        all_text.append(text)

    final_output = os.path.join(output_folder, "full_text.txt")
    with open(final_output, "w", encoding="utf-8") as f:
        f.write("\n".join(all_text))
        print(f"全文 OCR 完成，合并文件保存至 {final_output}")

    print(f"Extracted text from file using OCR.")
    return all_text

def get_existing_thumbnails(filename, output_folder):
    base_filename = os.path.splitext(filename)[0]
    existing_paths = []
    i = 1
    while True:
        output_path = os.path.join(output_folder, f"{base_filename}_page_{i}.png")
        if os.path.exists(output_path):
            existing_paths.append(f"/output/{base_filename}_page_{i}.png")
            i += 1
        else:
            break
    return existing_paths

def generate_pdf_thumbnails(file_path, output_folder, dpi=300):
    """將 PDF 文件每頁製作成縮圖。

    Args:
        pdf_path (str): PDF 檔案路徑。
        output_folder (str): 縮圖儲存資料夾路徑。
        dpi: 縮圖品質
    """
    try:
        # 將 PDF 轉換為圖片
        images = convert_from_path(file_path)
        output_paths = []
    
        # 保存每頁為 PNG 檔案
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        for i, image in enumerate(images):
            output_path = os.path.join(output_folder, f"{base_filename}_page_{i + 1}.png")
            image.save(output_path, 'PNG')
            output_paths.append(f"/output/{base_filename}_page_{i + 1}.png")
    
        return output_paths

    except Exception as e:
        print(f"製作縮圖時發生錯誤：{e}")
        return []



import logging
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import InputFormat

from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    EasyOcrOptions,
    OcrMacOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    TesseractOcrOptions,
)

from docling.document_converter import DocumentConverter, PdfFormatOption

from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
    InputFormat
)

from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline


def docling_extract_text_from_file(file_location, output_folder):

    logging.basicConfig(level=logging.INFO)

    """使用 Docling 提取 PDF 檔案中的文字"""
    try:
        input_doc_path = Path(file_location)

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        #pipeline_options.ocr_options = TesseractCliOcrOptions(lang=["chi_tra+eng+chi_sim"])
        pipeline_options.ocr_options = EasyOcrOptions(lang=["en", "ch_tra", "ch_sim"])
        pipeline_options.accelerator_options = AcceleratorOptions(num_threads=10, device=AcceleratorDevice.AUTO)

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        doc_converter = (
        DocumentConverter(  # all of the below is optional, has internal defaults.
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.IMAGE,
                    InputFormat.DOCX,
                    InputFormat.HTML,
                    InputFormat.PPTX,
                    InputFormat.ASCIIDOC,
                    InputFormat.CSV,
                    InputFormat.MD,
                ],  # whitelist formats, non-matching files are ignored.
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend
                    ),
                    InputFormat.DOCX: WordFormatOption(
                        pipeline_cls=SimplePipeline  # , backend=MsWordDocumentBackend
                    ),
                },
            )
        )

        conv_result = doc_converter.convert(input_doc_path)

        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        with (output_dir / f"full_text.txt").open("w", encoding="utf-8") as fp:
            fp.write(conv_result.document.export_to_text())

        with (output_dir / f"full_text.doctags").open("w", encoding="utf-8") as fp:
            fp.write(conv_result.document.export_to_document_tokens())

        all_text = conv_result.document.export_to_text()
        return all_text

    except Exception as e:
        logging.error(f"處理檔案 {file_location} 時發生錯誤：{e}")
        return f"Error: {e}" # 回傳錯誤訊息給前台
