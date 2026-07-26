import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional


class XmlParserResult:
    """Classe che rappresenta il risultato del parsing di un file XML"""

    def __init__(self):
        self.parts = []  # Lista di parti trovate nel file
        self.errors = []  # Eventuali errori durante il parsing
        self.warnings = []  # Avvertimenti durante il parsing

    @property
    def success(self) -> bool:
        """Indica se il parsing è stato completato con successo"""
        return len(self.errors) == 0

    @property
    def count(self) -> int:
        """Numero di parti trovate nel file"""
        return len(self.parts)


class XmlParser:
    """Classe per il parsing di file XML contenenti informazioni sui pezzi"""

    @staticmethod
    def parse_file(file_path: str) -> XmlParserResult:
        """Parsa un file XML e restituisce un oggetto XmlParserResult con i dati strutturati"""
        result = XmlParserResult()

        try:
            # Carica il file XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Processa gli elementi nel file XML
            XmlParser._parse_root(root, result)

        except ET.ParseError as e:
            result.errors.append(f"XML parsing error: {str(e)}")
            logging.error(f"XML parsing error: {str(e)}")
        except FileNotFoundError:
            result.errors.append(f"File not found: {file_path}")
            logging.error(f"File not found: {file_path}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            logging.error(f"Error parsing XML file: {str(e)}")

        return result

    @staticmethod
    def parse_string(xml_content: str) -> XmlParserResult:
        """Parsa una stringa XML e restituisce un oggetto XmlParserResult con i dati strutturati"""
        result = XmlParserResult()

        if not xml_content or not xml_content.strip():
            result.errors.append("No XML content provided")
            return result

        try:
            root = ET.fromstring(xml_content.strip())

            # Processa gli elementi nell'XML
            XmlParser._parse_root(root, result)

        except ET.ParseError as e:
            result.errors.append(f"XML parsing error: {str(e)}")
            logging.error(f"XML parsing error: {str(e)}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            logging.error(f"Error parsing XML content: {str(e)}")

        return result

    @staticmethod
    def _parse_root(root: ET.Element, result: XmlParserResult) -> None:
        """Processa gli elementi ITEM di un albero XML aggiungendoli al risultato"""
        for item in root.findall("ITEM"):
            part_data = XmlParser._parse_item(item)

            if part_data:
                result.parts.append(part_data)
            else:
                result.warnings.append(
                    f"Skipped item at position {len(result.parts) + len(result.warnings) + 1}"
                )

    @staticmethod
    def _parse_item(item: ET.Element) -> Optional[Dict[str, Any]]:
        """Parsa un singolo elemento ITEM dal file XML"""
        try:
            # Estrai i sottoelementi necessari
            item_type_elem = item.find("ITEMTYPE")
            item_id_elem = item.find("ITEMID")
            color_id_elem = item.find("COLOR")
            quantity_elem = item.find("MINQTY")

            # Verifica che tutti i campi obbligatori siano presenti
            if (
                item_type_elem is None
                or item_type_elem.text is None
                or item_id_elem is None
                or item_id_elem.text is None
                or color_id_elem is None
                or color_id_elem.text is None
                or quantity_elem is None
                or quantity_elem.text is None
            ):
                return None

            # Estrai i valori
            item_type = item_type_elem.text
            item_id = item_id_elem.text
            color_id = color_id_elem.text

            # Gestisci la quantità, con fallback su 1 in caso di errori
            try:
                quantity = int(quantity_elem.text)
                if quantity <= 0:
                    quantity = 1
            except (ValueError, TypeError):
                quantity = 1

            # Verifica che sia un pezzo (P) e non un set (S) o altro
            if item_type != "P":
                return None

            # Estrai informazioni aggiuntive opzionali
            extra_info = {}

            # Nome alternativo del pezzo
            alt_name = item.find("ITEMNAME")
            if alt_name is not None and alt_name.text:
                extra_info["alt_name"] = alt_name.text

            # Categoria
            category = item.find("CATEGORY")
            if category is not None and category.text:
                extra_info["category"] = category.text

            # Altre informazioni come peso, dimensioni, ecc.
            for key in ["WEIGHT", "WIDTH", "HEIGHT", "DEPTH"]:
                elem = item.find(key)
                if elem is not None and elem.text:
                    try:
                        extra_info[key.lower()] = float(elem.text)
                    except (ValueError, TypeError):
                        pass

            # Crea e restituisci il dizionario con i dati della parte
            return {
                "item_type": item_type,
                "part_id": item_id,
                "color_id": int(color_id),
                "quantity": quantity,
                "extra_info": extra_info,
            }

        except Exception as e:
            logging.warning(f"Error parsing item: {str(e)}")
            return None


class BrickLinkXmlParser(XmlParser):
    """Parser specializzato per file XML in formato BrickLink"""

    @staticmethod
    def _parse_item(item: ET.Element) -> Optional[Dict[str, Any]]:
        """Override del metodo per adattarsi al formato specifico di BrickLink"""
        try:
            # In BrickLink, i tag potrebbero avere nomi diversi
            item_type_elem = item.find("ITEMTYPE") or item.find("TYPE")
            item_id_elem = item.find("ITEMID") or item.find("ITEMNO")
            color_id_elem = item.find("COLOR")
            quantity_elem = item.find("MINQTY") or item.find("QTY")

            # Verifica che tutti i campi obbligatori siano presenti
            if None in (item_type_elem, item_id_elem, color_id_elem, quantity_elem):
                return None

            # Il resto è simile al parser base
            # ...
            # Chiama il metodo della classe padre con opportune modifiche
            return super(BrickLinkXmlParser, BrickLinkXmlParser)._parse_item(item)

        except Exception as e:
            logging.warning(f"Error parsing BrickLink item: {str(e)}")
            return None


class RebrickableXmlParser(XmlParser):
    """Parser specializzato per file XML in formato Rebrickable"""

    @staticmethod
    def _parse_item(item: ET.Element) -> Optional[Dict[str, Any]]:
        """Override del metodo per adattarsi al formato specifico di Rebrickable"""
        # Implementazione specifica per Rebrickable
        # ...
        pass
