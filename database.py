import xml.etree.ElementTree as ET
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from config import AppConfig
import logging

class BrickColor:
    def __init__(self, id: int, name: str, rgb: str, color_type: str):
        self.id = id
        self.name = name
        self.rgb = rgb
        self.type = color_type

class DatabaseManager:
    def __init__(self):
        self.db = None
        
    def initialize_database(self) -> bool:
        """Initialize the SQLite database connection and setup"""
        self.db = QSqlDatabase.addDatabase(AppConfig.DATABASE_TYPE)
        self.db.setDatabaseName(str(AppConfig.DATABASE_PATH))
        
        if not self.db.open():
            logging.error(f"Database Error: {self.db.lastError().text()}")
            return False
            
        # Create tables
        if not self._create_tables():
            return False
        
        # Check if colors_parts table is empty
        colorsPartsCount = self.getColorsPartsCount()
        if colorsPartsCount > 0:
            logging.info("Database already populated, skipping import")
            return True

        # Import reference data
        if not self.import_colors_from_xml():
            logging.warning("Failed to import colors data")
            
        if not self.import_categories_from_xml():
            logging.warning("Failed to import categories data")

        if not self.import_parts_from_xml():
            logging.warning("Failed to import parts data")

        if not self.import_color_parts_from_xml():
            logging.warning("Failed to import colors_parts data")
            
        return True
    
    def close_connection(self):
        """Close the database connection"""
        if self.db and self.db.isOpen():
            self.db.close()

    def getColorFromName(self, colorName: str) -> BrickColor:
        query = QSqlQuery()
        query.prepare("SELECT id,name,rgb,type FROM colors WHERE name = ?")
        query.addBindValue(colorName)
        if query.exec() and query.next():
            ret = BrickColor(query.value("id"), query.value("name"), query.value("rgb"), query.value("type"))
            return ret

        return None
    
    def getColorsPartsCount(self) -> int:
        query = QSqlQuery()
        if query.exec("SELECT COUNT(id) FROM colors_parts") and query.next():
            return query.value(0)
        else:
            return 0

    def addContainer(self, name: str, _description: str) -> bool:
        query = QSqlQuery()
        query.prepare("INSERT INTO containers (name) VALUES (?)")
        query.addBindValue(name)
        if not query.exec():
            logging.error(f"Error inserting container {name}: {query.lastError().text()}")
            return False
        return True
    
    def _create_tables(self) -> bool:
        """Create database tables using schema.sql"""
        try:
            if AppConfig.DATABASE_SCHEMA_PATH.exists():
                query = QSqlQuery()
                schema_sql = AppConfig.DATABASE_SCHEMA_PATH.read_text()
                
                # Split and execute multiple SQL statements
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        if not query.exec(statement):
                            logging.error(f"Query Error: {query.lastError().text()}")
                            return False
                return True
            else:
                logging.error("Schema file not found")
                return False
        except Exception as e:
            logging.error(f"Error creating tables: {str(e)}")
            return False
    
    def import_colors_from_xml(self) -> bool:
        """Import colors from the XML file into the colors table"""
        try:
            xml_path = AppConfig.DATABASE_DIR / "bricklink_data" / "colors.xml"
            if not xml_path.exists():
                logging.error(f"Colors XML file not found at {xml_path}")
                return False

            # Parse XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Start transaction for better performance
            self.db.transaction()

            # Clear existing data
            clear_query = QSqlQuery()
            if not clear_query.exec("DELETE FROM colors"):
                logging.error(f"Error clearing colors table: {clear_query.lastError().text()}")
                self.db.rollback()
                return False

            # Prepare insert query
            query = QSqlQuery()
            query.prepare("""
                INSERT INTO colors (id, name, rgb, type)
                VALUES (?, ?, ?, ?)
            """)

            # Process each color
            for item in root.findall('ITEM'):
                # Skip incomplete or empty entries
                color_elem = item.find('COLOR')
                name_elem = item.find('COLORNAME')
                if color_elem is None or name_elem is None or not color_elem.text:
                    logging.warning(f"Invalid xml codes for color_part!")
                    continue

                # Extract data
                color_id = int(color_elem.text)
                name = name_elem.text
                rgb = item.find('COLORRGB').text if item.find('COLORRGB').text is not None else ''
                color_type = item.find('COLORTYPE').text if item.find('COLORTYPE').text is not None else ''

                # if color_id == 0:
                #     continue

                # Bind values
                query.addBindValue(color_id)
                query.addBindValue(name)
                query.addBindValue(rgb)
                query.addBindValue(color_type)

                # Execute insert
                if not query.exec():
                    logging.error(f"Error inserting color {name}: {query.lastError().text()}")
                    self.db.rollback()
                    return False

            # Commit transaction
            if not self.db.commit():
                logging.error(f"Error committing transaction: {self.db.lastError().text()}")
                return False

            logging.info("Colors imported successfully")
            return True

        except Exception as e:
            logging.error(f"Error importing colors: {str(e)}")
            self.db.rollback()
            return False

    def import_categories_from_xml(self) -> bool:
        """Import categories from XML file into the categories table"""
        try:
            xml_path = AppConfig.DATABASE_DIR / "bricklink_data" / "categories.xml"
            if not xml_path.exists():
                logging.error(f"Categories XML file not found at {xml_path}")
                return False

            # Parse XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Start transaction
            self.db.transaction()

            # Clear existing data
            clear_query = QSqlQuery()
            if not clear_query.exec("DELETE FROM categories"):
                logging.error(f"Error clearing categories table: {clear_query.lastError().text()}")
                self.db.rollback()
                return False

            # Prepare insert query
            query = QSqlQuery()
            query.prepare("""
                INSERT INTO categories (id, name)
                VALUES (?, ?)
            """)

            # Process each category
            for item in root.findall('ITEM'):
                # Skip incomplete entries
                category_id = item.find('CATEGORY')
                name = item.find('CATEGORYNAME')
                
                if category_id is None or name is None:
                    logging.warning(f"Invalid xml codes for categories!")
                    continue

                # Extract data
                cat_id = int(category_id.text)
                cat_name = name.text.strip()

                # Bind values
                query.addBindValue(cat_id)
                query.addBindValue(cat_name)

                # Execute insert
                if not query.exec():
                    logging.error(f"Error inserting category {cat_name}: {query.lastError().text()}")
                    self.db.rollback()
                    return False

            # Commit transaction
            if not self.db.commit():
                logging.error(f"Error committing transaction: {self.db.lastError().text()}")
                return False

            logging.info("Categories imported successfully")
            return True

        except Exception as e:
            logging.error(f"Error importing categories: {str(e)}")
            self.db.rollback()
            return False

    def import_parts_from_xml(self) -> bool:
        """Import parts from XML file into the parts table"""
        try:
            xml_path = AppConfig.DATABASE_DIR / "bricklink_data" / "parts.xml"
            if not xml_path.exists():
                logging.error(f"Parts XML file not found at {xml_path}")
                return False

            # Parse XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Start transaction
            self.db.transaction()

            # Clear existing data
            clear_query = QSqlQuery()
            if not clear_query.exec("DELETE FROM parts"):
                logging.error(f"Error clearing parts table: {clear_query.lastError().text()}")
                self.db.rollback()
                return False

            # Prepare insert query
            query = QSqlQuery()
            query.prepare("""
                INSERT INTO parts (id, name, category, altid)
                VALUES (?, ?, ?, ?)
            """)

            # Process each part
            for item in root.findall('ITEM'):
                # Skip incomplete entries
                item_id = item.find('ITEMID')
                name = item.find('ITEMNAME')
                category = item.find('CATEGORY')
                altitemid = item.find('ALTITEMIDS')
                
                if item_id is None or name is None or category is None or altitemid is None:
                    logging.warning(f"Invalid xml codes for parts!")
                    continue

                # Extract data
                part_id = item_id.text.strip()
                part_name = name.text.strip()
                altid = altitemid.text.strip() if altitemid.text is not None else None
                if altid == '':
                    altid = None

                try:
                    category_id = int(category.text)
                except ValueError:
                    logging.warning(f"Invalid category ID for part {part_id}: {category.text}")
                    continue

                # Bind values
                query.addBindValue(part_id)
                query.addBindValue(part_name)
                query.addBindValue(category_id)
                query.addBindValue(altid)

                # Execute insert
                if not query.exec():
                    logging.error(f"Error inserting part {part_name}: {query.lastError().text()}")
                    self.db.rollback()
                    return False

            # Commit transaction
            if not self.db.commit():
                logging.error(f"Error committing transaction: {self.db.lastError().text()}")
                return False

            logging.info("Parts imported successfully")
            return True

        except Exception as e:
            logging.error(f"Error importing parts: {str(e)}")
            self.db.rollback()
            return False
        
    def import_color_parts_from_xml(self) -> bool:
        """Import codes from XML file into the color parts table"""
        try:
            xml_path = AppConfig.DATABASE_DIR / "bricklink_data" / "codes.xml"
            if not xml_path.exists():
                logging.error(f"Parts XML file not found at {xml_path}")
                return False

            # Parse XML file
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Start transaction
            self.db.transaction()

            # Clear existing data
            clear_query = QSqlQuery()
            if not clear_query.exec("DELETE FROM colors_parts"):
                logging.error(f"Error clearing colors_parts table: {clear_query.lastError().text()}")
                self.db.rollback()
                return False

            # Prepare insert query
            query = QSqlQuery()
            query.prepare("""
                INSERT INTO colors_parts (codename, color_id, part_id)
                VALUES (?, ?, ?)
            """)

            # Process each part
            for item in root.findall('ITEM'):
                # Skip incomplete entries
                item_id = item.find('ITEMID')
                colorname = item.find('COLOR')
                codename = item.find('CODENAME')
                
                if item_id is None or colorname is None or codename is None:
                    logging.warning(f"Invalid xml codes for color_part!")
                    continue

                # Extract data
                

                c = self.getColorFromName(colorname.text.strip())
                if c == None or c.id == None:
                    logging.warning(f"Invalid color in codes for color_part {codename.text} - {item_id.text}!")
                    continue

                color_id = c.id
                part_id = item_id.text.strip()

                try:
                    codenameNum = int(codename.text.strip())
                except ValueError:
                    logging.warning(f"Invalid item ID for color_part {part_id} - {colorname.text}: {codename.text}")
                    continue

                # Bind values
                query.addBindValue(codenameNum)
                query.addBindValue(color_id)
                query.addBindValue(part_id)


                # Execute insert
                if not query.exec():
                    logging.error(f"Error inserting color_part {part_id} - {colorname.text}: {query.lastError().text()}")
                    self.db.rollback()
                    return False

            # Commit transaction
            if not self.db.commit():
                logging.error(f"Error committing transaction: {self.db.lastError().text()}")
                return False

            logging.info("Parts imported successfully")
            return True

        except Exception as e:
            logging.error(f"Error importing parts: {str(e)}")
            self.db.rollback()
            return False