# utils/ocr_utils.py
"""
OCR 工具模組，提供檔案文字提取與 PDF 縮圖生成功能。
"""

import os
import shutil
import logging
from typing import List, Union
from pathlib import Path

import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    EasyOcrOptions,
    PdfPipelineOptions
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# 配置日誌
logging.basicConfig(level=logging.INFO)

def extract_text_from_file(file_location: str, output_folder: str) -> List[str]:
    """
    使用 OCR 從檔案中提取文字並儲存。

    Args:
        file_location (str): 輸入檔案的路徑。
        output_folder (str): 輸出文字檔案的資料夾。

    Returns:
        List[str]: 提取的文字列表。
    """
    dpi = 300
    lang = "chi_tra+eng"
    file_extension = os.path.splitext(file_location)[1].lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    all_text = []

    if file_extension == '.pdf':
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

            page_output = os.path.join(output_folder, f"page_{i + 1}.txt")
            with open(page_output, "w", encoding="utf-8") as file_handle:
                file_handle.write(text)
                print(f"Page {i + 1} OCR 完成，保存至 {page_output}")

    elif file_extension in image_extensions:
        img = Image.open(file_location)
        img_np = np.array(img)
        text = pytesseract.image_to_string(img_np, lang=lang, config="--psm 6 --oem 3")
        all_text.append(text)

    final_output = os.path.join(output_folder, "full_text.txt")
    with open(final_output, "w", encoding="utf-8") as file_handle:
        file_handle.write("\n".join(all_text))
        print(f"全文 OCR 完成，合併文件保存至 {final_output}")

    print("Extracted text from file using OCR.")
    return all_text

def get_existing_thumbnails(filename: str, output_folder: str) -> List[str]:
    """
    獲取指定檔案的現有縮圖路徑。

    Args:
        filename (str): 檔案名稱。
        output_folder (str): 縮圖儲存資料夾。

    Returns:
        List[str]: 現有縮圖的路徑列表。
    """
    base_filename = os.path.splitext(filename)[0]
    existing_paths = []
    page_num = 1
    while True:
        output_path = os.path.join(output_folder, f"{base_filename}_page_{page_num}.png")
        if os.path.exists(output_path):
            existing_paths.append(f"/output/{base_filename}_page_{page_num}.png")
            page_num += 1
        else:
            break
    return existing_paths

def generate_pdf_thumbnails(file_path: str, output_folder: str, dpi: int = 300) -> List[str]:
    """
    將 PDF 文件每頁製作成縮圖。

    Args:
        file_path (str): PDF 檔案路徑。
        output_folder (str): 縮圖儲存資料夾路徑。
        dpi (int): 縮圖品質，預設為 300。

    Returns:
        List[str]: 生成的縮圖路徑列表，若失敗則返回空列表。
    """
    try:
        images = convert_from_path(file_path)
        output_paths = []
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        for i, image in enumerate(images):
            output_path = os.path.join(output_folder, f"{base_filename}_page_{i + 1}.png")
            image.save(output_path, 'PNG')
            output_paths.append(f"/output/{base_filename}_page_{i + 1}.png")

        return output_paths

    except Exception as error:
        print(f"製作縮圖時發生錯誤：{error}")
        return []

def docling_extract_text_from_file(file_location: str, output_folder: str) -> Union[str, str]:
    """
    使用 Docling 從 PDF 檔案中提取文字。

    Args:
        file_location (str): 輸入檔案路徑。
        output_folder (str): 輸出文字檔案的資料夾。

    Returns:
        Union[str, str]: 提取的文字內容，若失敗則返回錯誤訊息。
    """
    try:
        input_doc_path = Path(file_location)

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        #pipeline_options.ocr_options = TesseractCliOcrOptions(lang=["chi_tra+eng+chi_sim"])
        pipeline_options.ocr_options = EasyOcrOptions(lang=["en", "ch_tra", "ch_sim"])
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=10,
            device=AcceleratorDevice.AUTO
        )

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline,
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend
                )
            }
        )

        conv_result = doc_converter.convert(input_doc_path)
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        full_text_path = output_dir / "full_text.txt"
        with full_text_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(conv_result.document.export_to_text())

        doctags_path = output_dir / "full_text.doctags"
        with doctags_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(conv_result.document.export_to_document_tokens())

        all_text = conv_result.document.export_to_text()
        return all_text

    except Exception as error:
        logging.error(f"處理檔案 {file_location} 時發生錯誤：{error}")
        return f"Error: {error}"
    
