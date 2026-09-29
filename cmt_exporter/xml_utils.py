"""xml.dom.minidom 文档的保存（缩进格式化）与片段插入。"""
import xml.dom.minidom


def append_xml_fragment(doc, parentnode, text):
    """把 XML 文本解析成片段，深拷贝后追加到 parentnode。"""
    fragment = xml.dom.minidom.parseString(text)
    parentnode.appendChild(doc.importNode(fragment.documentElement, deep=True))


def find_element_by_collection_name(parent_node, label, attr_name, sub_name, target_name):
    """按子节点 sub_name 属性等于 target_name 查找 label 元素；找不到返回 None。"""
    for element in parent_node.getElementsByTagName(label):
        names = element.getElementsByTagName(attr_name)
        if names and names[0].getAttribute(sub_name) == target_name:
            return element
    return None


def save_xml(doc, filepath, indent="  "):
    """完全重新格式化XML，无多余空白"""
    # 获取根元素
    root = doc.documentElement
    
    def format_node(node, level=0):
        """递归格式化节点"""
        indent_str = indent * level
        
        # 开始标签
        attrs = ""
        if node.attributes:
            attrs = " " + " ".join([f'{k}="{v}"' for k, v in node.attributes.items()])
        
        result = [f"{indent_str}<{node.tagName}{attrs}>"]
        
        # 处理子节点
        for child in node.childNodes:
            if child.nodeType == child.TEXT_NODE:
                text = child.nodeValue.strip()
                if text:
                    # 有文本内容
                    result.append(f"{indent_str}{indent}{text}")
            elif child.nodeType == child.ELEMENT_NODE:
                result.extend(format_node(child, level + 1))
        
        # 结束标签
        result.append(f"{indent_str}</{node.tagName}>")
        
        return result
    
    # 生成格式化后的XML
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.extend(format_node(root))
    
    # 保存
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
