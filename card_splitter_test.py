import cv2
import os
from card_splitter import CardSplitter

def main():
    # 使用相对路径读取测试图像
    image_path = "test.png"
    image = cv2.imread(image_path)
    
    if image is None:
        print("无法读取测试图像")
        return
    
    # 创建卡牌分割器实例
    splitter = CardSplitter()
    
    # 执行卡牌分割
    splitter.split_cards(image)
    
    print("纸牌分割完成，请查看cards目录")

if __name__ == "__main__":
    main()