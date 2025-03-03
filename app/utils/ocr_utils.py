# utils/ocr_utils.py
"""
OCR 工具模組，提供檔案文字提取與 PDF 縮圖生成功能。
"""
from typing import List, Union
from pathlib import Path

import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


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
    file_path = Path(file_location)
    file_extension = file_path.suffix.lower()
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    all_text = []
    output_dir = Path(output_folder)

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

            page_output = output_dir / f"page_{i + 1}.txt"
            with page_output.open("w", encoding="utf-8") as file_handle:
                file_handle.write(text)
                print(f"Page {i + 1} OCR 完成，保存至 {page_output}")

    elif file_extension in image_extensions:
        img = Image.open(file_location)
        img_np = np.array(img)
        text = pytesseract.image_to_string(img_np, lang=lang, config="--psm 6 --oem 3")
        all_text.append(text)

    final_output = output_dir / "full_text.txt"
    with final_output.open("w", encoding="utf-8") as file_handle:
        file_handle.write("\n".join(all_text))
        print(f"全文 OCR 完成，合併文件保存至 {final_output}")

    print("Extracted text from file using OCR.")
    return all_text

def get_existing_thumbnails(filename: str, output_folder: str) -> List[str]:
    """
    獲取指定檔案的現有縮圖路徑。

    Args:
        filename (str): 檔案名稱。
        output_folder (str): 縮圖儲存子目錄（例如 output/<filename>）。

    Returns:
        List[str]: 現有縮圖的路徑列表。
    """
    output_dir = Path(output_folder)
    base_filename = Path(filename).stem
    existing_paths = []
    page_num = 1
    while True:
        output_path = output_dir / f"{base_filename}_page_{page_num}.png"
        if output_path.exists():
            # 更新路徑以反映子目錄結構
            existing_paths.append(f"/output/{base_filename}/{base_filename}_page_{page_num}.png")
            page_num += 1
        else:
            break
    return existing_paths

def generate_pdf_thumbnails(file_path: str, output_folder: str, dpi: int = 300) -> List[str]:
    """
    將 PDF 文件每頁製作成縮圖。

    Args:
        file_path (str): PDF 檔案路徑。
        output_folder (str): 縮圖儲存子目錄（例如 output/<filename>）。
        dpi (int): 縮圖品質，預設為 300。

    Returns:
        List[str]: 生成的縮圖路徑列表，若失敗則返回空列表。
    """
    try:
        images = convert_from_path(file_path)
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)  # 確保子目錄存在
        output_paths = []
        base_filename = Path(file_path).stem

        for i, image in enumerate(images):
            output_path = output_dir / f"{base_filename}_page_{i + 1}.png"
            image.save(str(output_path), 'PNG')
            # 更新路徑以反映子目錄結構
            output_paths.append(f"/output/{base_filename}/{base_filename}_page_{i + 1}.png")

        return output_paths

    except Exception as error:
        print(f"製作縮圖時發生錯誤：{error}")
        return []


from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
    InputFormat,
)
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from pathlib import Path
import json
import logging

def docling_extract_text_from_file(file_location: str, output_folder: str) -> str:
    """
    使用 Docling 從不同類型文件中提取文字和表格內容。

    Args:
        file_location (str): 輸入檔案路徑。
        output_folder (str): 輸出文字和表格檔案的子目錄（例如 output/<filename>）。

    Returns:
        str: 提取的文字內容，若失敗則返回錯誤訊息。
    """
    try:
        input_doc_path = Path(file_location)
        if not input_doc_path.exists():
            raise FileNotFoundError(f"檔案不存在: {file_location}")

        logging.info(f"處理檔案: {input_doc_path.absolute()}")

        # 定義 OCR 選項，支持英文和中文（繁體、簡體）
        ocr_options = EasyOcrOptions(lang=["en", "ch_tra"])

        # 定義 PDF 的管道選項，啟用 OCR 和表格結構提取
        pdf_pipeline_options = PdfPipelineOptions()
        pdf_pipeline_options.do_ocr = True
        pdf_pipeline_options.do_table_structure = True
        pdf_pipeline_options.table_structure_options.do_cell_matching = True
        pdf_pipeline_options.ocr_options = ocr_options
        pdf_pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=10,
            device=AcceleratorDevice.AUTO
        )

        # 根據文件類型設置格式選項
        extension = input_doc_path.suffix.lower()
        format_options = {}
        if extension == ".pdf":
            format_options[InputFormat.PDF] = PdfFormatOption(
                pipeline_cls=StandardPdfPipeline,
                pipeline_options=pdf_pipeline_options,
                backend=PyPdfiumDocumentBackend
            )
        elif extension in [".docx", ".doc"]:
            format_options[InputFormat.WORD] = WordFormatOption()
        else:
            raise ValueError(f"不支援的文件類型: {extension}")

        # 初始化 DocumentConverter
        doc_converter = DocumentConverter(format_options=format_options)
        conv_result = doc_converter.convert(input_doc_path)

        # 獲取文檔對象
        document = conv_result.document

        # 創建輸出子目錄
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 獲取基本文件名（不含擴展名）
        base_filename = input_doc_path.stem

        # 保存完整文字內容（TXT 格式）
        full_text_path = output_dir / f"{base_filename}_full_text.txt"
        with full_text_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(document.export_to_text())

        # 保存完整文字內容（Markdown 格式）
        full_text_md_path = output_dir / f"{base_filename}_full_text.md"
        with full_text_md_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(document.export_to_markdown())

        # 保存文檔標記
        doctags_path = output_dir / f"{base_filename}_full_text.doctags"
        with doctags_path.open("w", encoding="utf-8") as file_handle:
            file_handle.write(document.export_to_document_tokens())

        # 保存表格數據（若存在）
        tables = document.tables
        if tables:
            table_data = []
            for table in tables:
                table_dict = {"rows": table.rows}
                table_data.append(table_dict)
            table_json_path = output_dir / f"{base_filename}_tables.json"
            with table_json_path.open("w", encoding="utf-8") as f:
                json.dump(table_data, f)

        # 返回完整文字內容
        all_text = document.export_to_text()
        return all_text

    except Exception as error:
        logging.error(f"處理檔案 {file_location} 時失敗：{str(error)}", exc_info=True)
        return f"錯誤: {error}"
