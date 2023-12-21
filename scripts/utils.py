import base64
import cv2
import pyshine as ps

from colorama import Fore, Style


def print_with_color(text: str, color=""):
    if color == "red":
        print(Fore.RED + text)
    elif color == "green":
        print(Fore.GREEN + text)
    elif color == "yellow":
        print(Fore.YELLOW + text)
    elif color == "blue":
        print(Fore.BLUE + text)
    elif color == "magenta":
        print(Fore.MAGENTA + text)
    elif color == "cyan":
        print(Fore.CYAN + text)
    elif color == "white":
        print(Fore.WHITE + text)
    elif color == "black":
        print(Fore.BLACK + text)
    else:
        print(text)
    print(Style.RESET_ALL)


def draw_bbox_multi(img_path, output_path, elem_list, record_mode=False, dark_mode=False):
    imgcv = cv2.imread(img_path)
    count = 1
    for elem in elem_list:
        try:
            top_left = elem.bbox[0]
            bottom_right = elem.bbox[1]
            left, top = top_left[0], top_left[1]
            right, bottom = bottom_right[0], bottom_right[1]
            label = str(count)
            if record_mode:
                if elem.attrib == "clickable":
                    color = (250, 0, 0)
                elif elem.attrib == "focusable":
                    color = (0, 0, 250)
                else:
                    color = (0, 250, 0)
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10, text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=color,
                                    text_RGB=(255, 250, 250), alpha=0.5)
            else:
                text_color = (10, 10, 10) if dark_mode else (255, 250, 250)
                bg_color = (255, 250, 250) if dark_mode else (10, 10, 10)
                imgcv = ps.putBText(imgcv, label, text_offset_x=(left + right) // 2 + 10, text_offset_y=(top + bottom) // 2 + 10,
                                    vspace=10, hspace=10, font_scale=1, thickness=2, background_RGB=bg_color,
                                    text_RGB=text_color, alpha=0.5)
        except Exception as e:
            print_with_color(f"ERROR: An exception occurs while labeling the image\n{e}", "red")
        count += 1
    cv2.imwrite(output_path, imgcv)
    return imgcv


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
