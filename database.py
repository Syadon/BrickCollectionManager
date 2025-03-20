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

class Container:
    def __init__(self, id: int, name: str, description: str, part_count: int = 0, lot_count:int = 0):
        self.id = id
        self.name = name
        self.description = description
        self.part_count = part_count if part_count != None else 0
        self.lot_count = lot_count if lot_count != None else 0
    
class ColorPart:
    def __init__(self, id:int, part_id: str, color_id: int):
        self.id = id
        self.part_id = part_id
        self.color_id = color_id

class DatabaseManager:
    def __init__(self):
        self.db = QSqlDatabase.database()
    
    def initialize_database(self) -> bool:
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
        
    def getContainers(self) -> list[Container]:
        containers = []
        query = QSqlQuery("SELECT * FROM containers")
        while query.next():
            container = Container(
                query.value("id"),
                query.value("name"),
                query.value("description"),
                self.getConteinerPartCount(query.value("id")),
                self.getConteinerLotCount(query.value("id"))
            )
            containers.append(container)
        return containers
    
    def getColors(self) -> list[BrickColor]:
        query = QSqlQuery("SELECT * FROM colors ORDER BY name")
        colors = []
        while query.next():
            color = BrickColor(
                query.value("id"),
                query.value("name"),
                query.value("rgb"),
                query.value("type")
            )
            colors.append(color)
        return colors
    
    def getColorsNames(self) -> list[str]:
        ret = []
        query = QSqlQuery("SELECT DISTINCT name FROM colors ORDER BY name")
        while query.next():
            ret.append(query.value("name"))

        return ret
    
    def getAllPartsIds(self) -> list[str]:
        part_ids = []
        query = QSqlQuery("""
            SELECT DISTINCT p.id 
            FROM parts p
            JOIN colors_parts cp ON p.id = cp.part_id
            JOIN parts_collection pc ON cp.id = pc.item
            ORDER BY p.id
        """)
        
        while query.next():
            part_ids.append(query.value(0))
            
        return part_ids
    
    def getAllPartsNames(self) -> list[str]:
        part_names = []
        query = QSqlQuery("""
            SELECT DISTINCT p.name 
            FROM parts p
            JOIN colors_parts cp ON p.id = cp.part_id
            JOIN parts_collection pc ON cp.id = pc.item
            ORDER BY p.name
        """)
        
        while query.next():
            part_names.append(query.value(0))
            
        return part_names
    
    def getColorsTypesNames(self) -> list[str]:
        ret = []
        query = QSqlQuery("SELECT DISTINCT type FROM colors ORDER BY type")
        while query.next():
            ret.append(query.value("type"))

        return ret
        
    def searchIntoCollection(self, part_id: str = None, part_name: str = None, 
                             color_name: str = None, color_type: str = None) -> list[dict]:
        # Build query based on search criteria
        query_str = """
            SELECT cp.id, p.id as part_id, p.name as part_name, 
                cp.color_id as color_id, c.name as color_name, c.rgb as color_rgb,
                c.type as color_type, cat.name as part_category,
                con.name as container_name, pc.count as quantity,
                con.id as container_id
            FROM parts_collection pc
            JOIN colors_parts cp ON pc.item = cp.id
            JOIN parts p ON cp.part_id = p.id
            JOIN colors c ON cp.color_id = c.id
            JOIN containers con ON pc.container_id = con.id
            JOIN categories cat ON p.category = cat.id
            WHERE 1=1
        """
        
        params = []
        
        # Part ID filter
        if part_id:
            query_str += " AND p.id = ?"
            params.append(part_id)
            
        # Part Name filter
        elif part_name:
            query_str += " AND p.name LIKE ?"
            params.append(f"%{part_name}%")
            
        # Color filter
        if color_name:
            query_str += " AND c.name = ?"
            params.append(color_name)
            
        # Color Type filter
        if color_type:
            query_str += " AND c.type = ?"
            params.append(color_type)
            
        query_str += " ORDER BY p.name, c.name, con.name"
        
        # Execute query
        query = QSqlQuery()
        query.prepare(query_str)
        
        for param in params:
            query.addBindValue(param)
            
        if not query.exec():
            logging.warning(f"Failed to serach into collection: {query.lastError().text()}")
            return []
            
        # Process results
        results = []
        while query.next():
            results.append({
                'id': query.value('id'),
                'part_id': query.value('part_id'),
                'part_name': query.value('part_name'),
                'part_category': query.value('part_category'),
                'color_id': query.value('color_id'),
                'color_name': query.value('color_name'),
                'rgb': query.value('color_rgb'),
                'color_type': query.value('color_type'),
                'container_name': query.value('container_name'),
                'quantity': query.value('quantity'),
                'container_id': query.value('container_id')
            })

        return results

    def getPartColors(self, part_id: str) -> list[BrickColor]:
        # Create SQL query to get colors for part
        query = QSqlQuery()
        query.prepare("""
            SELECT DISTINCT c.id, c.name, c.rgb, c.type
            FROM colors c
            JOIN colors_parts cp ON c.id = cp.color_id
            WHERE cp.part_id = ?
            ORDER BY c.name
        """)
        query.addBindValue(part_id)
        
        if query.exec():
            colors = []
            while query.next():
                color = BrickColor(
                    query.value("id"),
                    query.value("name"),
                    query.value("rgb"),
                    query.value("type")
                )
                colors.append(color)
            return colors
        else:
            return []

    def getConteinerPartCount(self, container_id: int) -> int:
        query = QSqlQuery()
        query.prepare("SELECT SUM(count) FROM parts_collection WHERE container_id = ?")
        query.addBindValue(container_id)
        if query.exec() and query.next():
            val = query.value(0)
            return val if val != None and val != '' else 0
        else:
            return None
        
    def getConteinerLotCount(self, container_id: int) -> int:
        query = QSqlQuery()
        query.prepare("SELECT COUNT(*) FROM parts_collection WHERE container_id = ? AND count > 0")
        query.addBindValue(container_id)
        if query.exec() and query.next():
            val = query.value(0)
            return val if val != None and val != '' else 0
        else:
            return None

    def addContainer(self, name: str, description: str) -> bool:
        query = QSqlQuery()
        query.prepare("INSERT INTO containers (name, description) VALUES (?, ?)")
        query.addBindValue(name)
        query.addBindValue(description)
        if not query.exec():
            logging.error(f"Error inserting container {name}: {query.lastError().text()}")
            return False
        return True
    
    def getColorPart(self, part_id: str, color_id: int) -> int:
        query = QSqlQuery()
        query.prepare("SELECT id FROM colors_parts WHERE part_id = ? AND color_id = ?")
        query.addBindValue(part_id)
        query.addBindValue(color_id)
        if query.exec() and query.next():
            return ColorPart(query.value("id"), part_id, color_id)
        else:
            return None

    def addColorPartToContainer(self, colorPart: ColorPart, container_id: int, quantity: int) -> bool:
        return self.addColorPartIDToContainer(colorPart.id, container_id, quantity)
    
    def addColorPartIDToContainer(self, colorPartID: int, container_id: int, quantity: int) -> bool:
        self.db.transaction()
        try:
            if not self.addColorPartIDToContainerNoTrans(colorPartID, container_id, quantity):
                self.db.rollback()
                return False
            else:
                self.db.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding part to container: {str(e)}")
            self.db.rollback()
            return False
    
    def addColorPartIDToContainerNoTrans(self, colorPartID: int, container_id: int, quantity: int) -> bool:
        try:
            query = QSqlQuery()

            if quantity > 0:
                query.prepare("""INSERT OR IGNORE INTO parts_collection (item, container_id, count) VALUES (?, ?, 0);""")
                query.addBindValue(colorPartID)
                query.addBindValue(container_id)
                if not query.exec():
                    logging.error(f"Error adding part to collection: {query.lastError().text()}")
                    return False
            
            query.prepare("""UPDATE parts_collection SET count = count + ? WHERE item = ? AND container_id = ?""")
            query.addBindValue(quantity)
            query.addBindValue(colorPartID)
            query.addBindValue(container_id)
            if not query.exec():
                logging.error(f"Error updating part count: {query.lastError().text()}")
                return False
            
            if quantity < 0:
                if not self.removeZeroQtyEntries(container_id):
                    return False

            return True
    
        except Exception as e:
            logging.error(f"Error moving parts: {str(e)}")
            return False
    
    def removeZeroQtyEntries(self, container_id: int) -> bool:
        try:
            query = QSqlQuery()
            query.prepare("DELETE FROM parts_collection WHERE container_id = ? AND count = 0")
            query.addBindValue(container_id)
            if not query.exec():
                logging.error(f"Error removing zero quantity entries: {query.lastError().text()}")
                return False

            return True
        except Exception as e:
            logging.error(f"Error cleaning zero qty {container_id}: {str(e)}")
            return False
        
    def movePartsBetweenContainers(self, part_id: str, source_container_id: int, target_container_id: int, quantity: int) -> bool:
        # Start transaction
        self.db.transaction()

        try:
            # Remove from source container
            if not self.addColorPartIDToContainerNoTrans(part_id, source_container_id, -quantity):
                self.db.rollback()
                return False
                
            # Add to target container
            if not self.addColorPartIDToContainerNoTrans(part_id, target_container_id, quantity):
                self.db.rollback()
                return False
                
            # Remove zero quantity entries
            if not self.removeZeroQtyEntries(source_container_id):
                self.db.rollback()
                return False
                
            # Commit transaction
            if not self.db.commit():
                logging.error(f"Error committing transaction: {self.db.lastError().text()}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error moving parts: {str(e)}")
            self.db.rollback()
            return False
    
    def updateContainer(self, container: Container) -> bool:
        try:
            query = QSqlQuery()
            query.prepare("""
                UPDATE containers 
                SET name = ?, description = ?
                WHERE id = ?
            """)
            query.addBindValue(container.name)
            query.addBindValue(container.description)
            query.addBindValue(container.id)
            
            if not query.exec():
                logging.error(f"Error updating container: {query.lastError().text()}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error updating container: {str(e)}")
            return False
        
    def getContainersParts(self, container_id):
        parts_data = []
        try:
            query = QSqlQuery()
            query.prepare("""
                SELECT cp.id, p.id as part_id, p.name as part_name, 
                    c.name as color_name, pc.count as quantity,
                    c.id as color_id, cat.name as part_category,
                    c.rgb as rgb, c.type as color_type
                FROM parts_collection pc
                JOIN colors_parts cp ON pc.item = cp.id
                JOIN parts p ON cp.part_id = p.id
                JOIN colors c ON cp.color_id = c.id
				JOIN categories cat ON p.category = cat.id
                WHERE pc.container_id = ?
                ORDER BY p.name, c.name
            """)
            query.addBindValue(container_id)

            if query.exec():
                while query.next():
                    parts_data.append({
                        'id': query.value('id'),
                        'part_id': query.value('part_id'),
                        'part_name': query.value('part_name'),
                        'part_category': query.value('part_category'),
                        'color_name': query.value('color_name'),
                        'quantity': query.value('quantity'),
                        'color_id': query.value('color_id'),
                        'rgb': query.value('rgb'),
                        'color_type': query.value('color_type')
                    })
        except Exception as e:
            logging.error(f"Error updating container: {str(e)}")
            return []
        
        return parts_data

    def _create_tables(self) -> bool:
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
            
            clear_query = QSqlQuery()
            if not clear_query.exec("DELETE FROM colors_parts_codenames"):
                logging.error(f"Error clearing colors_parts table: {clear_query.lastError().text()}")
                self.db.rollback()
                return False

            # Prepare insert query
            query = QSqlQuery()
            query.prepare("""
                INSERT OR IGNORE INTO colors_parts (color_id, part_id)
                VALUES (?, ?)
            """)

            queryCodename = QSqlQuery()
            queryCodename.prepare("""
                INSERT OR IGNORE INTO colors_parts_codenames (codename, color_part)
                VALUES (?, ?)
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
                query.addBindValue(color_id)
                query.addBindValue(part_id)


                # Execute insert
                if not query.exec():
                    logging.error(f"Error inserting color_part {part_id} - {colorname.text}: {query.lastError().text()}")
                    self.db.rollback()
                    return False
                
                ret = query.lastInsertId()
                queryCodename.addBindValue(codenameNum)
                queryCodename.addBindValue(ret)

                if not queryCodename.exec():
                    logging.error(f"Error inserting codename {part_id} - {colorname.text} - {ret}: {queryCodename.lastError().text()}")
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

    def deleteContainer(self, container_id):
        try:
            # Check if container has parts
            query = QSqlQuery()
            query.prepare("SELECT COUNT(*) FROM parts_collection WHERE container_id = ?")
            query.addBindValue(container_id)
            
            if query.exec() and query.next():
                count = query.value(0)
                if count > 0:
                    logging.error("Cannot delete container with parts")
                    return False
                    
            # Delete container
            query.prepare("DELETE FROM containers WHERE id = ?")
            query.addBindValue(container_id)
            
            return query.exec()
            
        except Exception as e:
            logging.error(f"Error deleting container: {str(e)}")
            return False

    def moveAllParts(self, source_container_id, target_container_id):
        try:
            # Start transaction
            self.db.transaction()
            
            # Get parts in source container
            query = QSqlQuery()
            query.prepare("SELECT item, count FROM parts_collection WHERE container_id = ?")
            query.addBindValue(source_container_id)
            
            if not query.exec():
                logging.error(f"Error querying parts: {query.lastError().text()}")
                self.db.rollback()
                return False
            
            # Process each part
            while query.next():
                item_id = query.value(0)
                count = query.value(1)
                
                # Check if part already exists in target
                check_query = QSqlQuery()
                check_query.prepare("SELECT count FROM parts_collection WHERE item = ? AND container_id = ?")
                check_query.addBindValue(item_id)
                check_query.addBindValue(target_container_id)
                
                if check_query.exec() and check_query.next():
                    # Update existing entry
                    update_query = QSqlQuery()
                    update_query.prepare("UPDATE parts_collection SET count = count + ? WHERE item = ? AND container_id = ?")
                    update_query.addBindValue(count)
                    update_query.addBindValue(item_id)
                    update_query.addBindValue(target_container_id)
                    
                    if not update_query.exec():
                        logging.error(f"Error updating part: {update_query.lastError().text()}")
                        self.db.rollback()
                        return False
                else:
                    # Insert new entry
                    insert_query = QSqlQuery()
                    insert_query.prepare("INSERT INTO parts_collection (item, count, container_id) VALUES (?, ?, ?)")
                    insert_query.addBindValue(item_id)
                    insert_query.addBindValue(count)
                    insert_query.addBindValue(target_container_id)
                    
                    if not insert_query.exec():
                        logging.error(f"Error inserting part: {insert_query.lastError().text()}")
                        self.db.rollback()
                        return False
            
            # Delete all parts from source container
            delete_query = QSqlQuery()
            delete_query.prepare("DELETE FROM parts_collection WHERE container_id = ?")
            delete_query.addBindValue(source_container_id)
            
            if not delete_query.exec():
                logging.error(f"Error deleting parts: {delete_query.lastError().text()}")
                self.db.rollback()
                return False
                
            # Commit transaction
            return self.db.commit()
            
        except Exception as e:
            logging.error(f"Error moving parts: {str(e)}")
            self.db.rollback()
            return False

    def deleteContainerWithParts(self, container_id):
        try:
            # Start transaction
            self.db.transaction()
            
            # Delete all parts
            query = QSqlQuery()
            query.prepare("DELETE FROM parts_collection WHERE container_id = ?")
            query.addBindValue(container_id)
            
            if not query.exec():
                logging.error(f"Error deleting parts: {query.lastError().text()}")
                self.db.rollback()
                return False
                
            # Delete container
            query.prepare("DELETE FROM containers WHERE id = ?")
            query.addBindValue(container_id)
            
            if not query.exec():
                logging.error(f"Error deleting container: {query.lastError().text()}")
                self.db.rollback()
                return False
                
            # Commit transaction
            return self.db.commit()
            
        except Exception as e:
            logging.error(f"Error deleting container: {str(e)}")
            self.db.rollback()
            return False

    def searchColorsParts(self, part_id=None, part_name=None, color_name=None, color_type=None):
        """Cerca colors_parts in base ai criteri specificati"""
        query_str = """
            SELECT cp.id, p.id as part_id, p.name as part_name, 
                   c.id as color_id, c.name as color_name, c.type as color_type,
                   c.rgb as rgb
            FROM colors_parts cp
            JOIN parts p ON cp.part_id = p.id
            JOIN colors c ON cp.color_id = c.id
            WHERE 1=1
        """
        
        params = []
        
        # Filtro Part ID
        if part_id:
            query_str += " AND p.id = ?"
            params.append(part_id)
            
        # Filtro Part Name
        elif part_name:
            query_str += " AND p.name LIKE ?"
            params.append(f"%{part_name}%")
            
        # Filtro Color
        if color_name:
            query_str += " AND c.name = ?"
            params.append(color_name)
            
        # Filtro Color Type
        if color_type:
            query_str += " AND c.type = ?"
            params.append(color_type)
            
        query_str += " ORDER BY p.name, c.name"
        
        # Esegui query
        query = QSqlQuery()
        query.prepare(query_str)
        
        for param in params:
            query.addBindValue(param)
            
        if not query.exec():
            logging.warning(f"Failed to search colors_parts: {query.lastError().text()}")
            return []
            
        # Processa risultati
        results = []
        while query.next():
            results.append({
                'id': query.value('id'),
                'part_id': query.value('part_id'),
                'part_name': query.value('part_name'),
                'color_id': query.value('color_id'),
                'color_name': query.value('color_name'),
                'color_type': query.value('color_type'),
                'rgb': query.value('rgb')
            })
            
        return results