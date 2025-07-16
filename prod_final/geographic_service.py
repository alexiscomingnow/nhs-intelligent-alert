#!/usr/bin/env python3
"""
地理位置服务
处理邮编距离计算和医院地理过滤
"""

import sqlite3
import math
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class GeographicService:
    """地理位置服务"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        # 英国主要邮编区域的大致坐标 (简化版本)
        self.postcode_coordinates = self._initialize_postcode_coordinates()
        
        # 简化的医院位置数据
        self.hospital_locations = self._initialize_hospital_locations()
    
    def _initialize_postcode_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """初始化邮编坐标数据 - 扩展版本"""
        return {
            # 伦敦地区邮编
            'SW1A': (51.5014, -0.1419),  # Westminster
            'WC1A': (51.5074, -0.1278),  # Holborn
            'EC1A': (51.5155, -0.0922),  # City of London
            'NW1': (51.5289, -0.1235),   # Camden
            'SE1': (51.5010, -0.1043),   # Southwark
            'E1': (51.5151, -0.0454),    # Tower Hamlets
            'W1A': (51.5152, -0.1441),   # West End
            'N1': (51.5390, -0.1026),    # Islington
            'SW3': (51.4901, -0.1692),   # Chelsea
            'W2': (51.5156, -0.1816),    # Paddington
            
            # 其他主要英格兰城市
            'M1': (53.4808, -2.2426),    # Manchester
            'M2': (53.4839, -2.2446),    # Manchester City Centre
            'M3': (53.4770, -2.2309),    # Manchester
            'B1': (52.4862, -1.8904),    # Birmingham
            'B2': (52.4796, -1.8978),    # Birmingham
            'B3': (52.4887, -1.8816),    # Birmingham
            'LS1': (53.8008, -1.5491),   # Leeds
            'LS2': (53.7974, -1.5437),   # Leeds
            'LS3': (53.8067, -1.5689),   # Leeds
            'L1': (53.4084, -2.9916),    # Liverpool
            'L2': (53.4019, -2.9802),    # Liverpool
            'L3': (53.4106, -2.9883),    # Liverpool
            'S1': (53.3811, -1.4701),    # Sheffield
            'S2': (53.3665, -1.4921),    # Sheffield
            'S3': (53.3849, -1.4659),    # Sheffield
            'NE1': (54.9783, -1.6178),   # Newcastle
            'NE2': (54.9823, -1.6178),   # Newcastle
            'NE3': (54.9889, -1.6306),   # Newcastle
            'BS1': (51.4545, -2.5879),   # Bristol
            'BS2': (51.4584, -2.5721),   # Bristol
            'BS3': (51.4398, -2.6103),   # Bristol
            'CB1': (52.2053, 0.1218),    # Cambridge
            'CB2': (52.1985, 0.1255),    # Cambridge
            'CB3': (52.2155, 0.0906),    # Cambridge
            'OX1': (51.7520, -1.2577),   # Oxford
            'OX2': (51.7467, -1.2674),   # Oxford
            'OX3': (51.7441, -1.2345),   # Oxford
            
            # 苏格兰主要邮编
            'EH1': (55.9533, -3.1883),   # Edinburgh City Centre
            'EH2': (55.9570, -3.2053),   # Edinburgh New Town
            'EH3': (55.9570, -3.2200),   # Edinburgh West End
            'EH4': (55.9725, -3.2267),   # Edinburgh Davidson's Mains
            'EH5': (55.9767, -3.1931),   # Edinburgh Newhaven
            'EH6': (55.9767, -3.1738),   # Edinburgh Leith
            'EH7': (55.9614, -3.1738),   # Edinburgh Leith
            'EH8': (55.9478, -3.1820),   # Edinburgh Marchmont
            'EH9': (55.9350, -3.1820),   # Edinburgh Liberton
            'EH10': (55.9261, -3.2028),  # Edinburgh Morningside
            'G1': (55.8642, -4.2518),    # Glasgow City Centre
            'G2': (55.8578, -4.2720),    # Glasgow Merchant City
            'G3': (55.8721, -4.2720),    # Glasgow Finnieston
            'G4': (55.8721, -4.2518),    # Glasgow Cowcaddens
            'G5': (55.8470, -4.2518),    # Glasgow Gorbals
            
            # 威尔士主要邮编
            'CF1': (51.4816, -3.1791),   # Cardiff City Centre
            'CF2': (51.4894, -3.1791),   # Cardiff
            'CF3': (51.4702, -3.1389),   # Cardiff
            'CF10': (51.4894, -3.1916),  # Cardiff Bay
            'CF11': (51.4702, -3.1916),  # Cardiff
            'CF14': (51.5152, -3.2389),  # Cardiff
            'CF15': (51.5194, -3.2389),  # Cardiff
            'CF23': (51.5194, -3.1389),  # Cardiff
            'CF24': (51.4894, -3.1389),  # Cardiff
            'SA1': (51.6214, -3.9436),   # Swansea
            'SA2': (51.6009, -3.9889),   # Swansea
            'SA3': (51.5753, -4.0389),   # Swansea
            
            # 北爱尔兰主要邮编（重点扩展）
            'BT1': (54.5973, -5.9301),   # Belfast City Centre
            'BT2': (54.5973, -5.8801),   # Belfast East
            'BT3': (54.6173, -5.8801),   # Belfast North
            'BT4': (54.5773, -5.8801),   # Belfast East
            'BT5': (54.5573, -5.8301),   # Belfast South East
            'BT6': (54.5573, -5.8801),   # Belfast South
            'BT7': (54.5773, -5.9301),   # Belfast South
            'BT8': (54.5373, -5.9301),   # Belfast South
            'BT9': (54.5773, -5.9801),   # Belfast South West
            'BT10': (54.5573, -5.9801),  # Belfast South West
            'BT11': (54.5373, -5.9801),  # Belfast West
            'BT12': (54.5773, -6.0301),  # Belfast West
            'BT13': (54.6173, -5.9801),  # Belfast North West
            'BT14': (54.6373, -5.9801),  # Belfast North
            'BT15': (54.6373, -5.9301),  # Belfast North
            'BT16': (54.5573, -5.7801),  # Dundonald
            'BT17': (54.5373, -6.0801),  # Belfast South West
            'BT18': (54.6573, -5.6801),  # Holywood
            'BT19': (54.6773, -5.6301),  # Bangor
            'BT20': (54.6973, -5.5801),  # Bangor
            'BT21': (54.3573, -5.7301),  # Saintfield
            'BT22': (54.4773, -5.7301),  # Killyleagh
            'BT23': (54.5173, -5.7301),  # Newtownards
            'BT24': (54.3373, -5.8301),  # Ballynahinch
            'BT25': (54.2573, -5.8801),  # Dromore
            'BT26': (54.4373, -6.0801),  # Moira
            'BT27': (54.5173, -6.0801),  # Lisburn
            'BT28': (54.5373, -6.0301),  # Lisburn
            'BT29': (54.6173, -6.1801),  # Crumlin
            'BT30': (54.3173, -5.6301),  # Downpatrick
            'BT31': (54.2373, -5.6801),  # Kilkeel
            'BT32': (54.1973, -5.9301),  # Banbridge
            'BT33': (54.1573, -6.0301),  # Newry
            'BT34': (54.1373, -6.1301),  # Newry
            'BT35': (54.1773, -6.2301),  # Newry
            'BT36': (54.6773, -5.9301),  # Newtownabbey
            'BT37': (54.7173, -5.9801),  # Newtownabbey (用户的邮编!)
            'BT38': (54.7373, -5.8301),  # Carrickfergus
            'BT39': (54.7573, -5.7801),  # Ballyclare
            'BT40': (54.8573, -5.7801),  # Larne
            'BT41': (54.8773, -6.2801),  # Antrim
            'BT42': (55.0173, -6.2301),  # Ballymena
            'BT43': (55.0573, -6.2801),  # Ballymena
            'BT44': (55.0973, -6.5301),  # Ballymoney
            'BT45': (54.9773, -6.6801),  # Magherafelt
            'BT46': (54.9573, -6.7801),  # Maghera
            'BT47': (55.0273, -7.3201),  # Londonderry
            'BT48': (55.0073, -7.3201),  # Londonderry
            'BT49': (55.1773, -6.6301),  # Limavady
            'BT50': (55.2273, -6.5801),  # Coleraine
            'BT51': (55.1573, -6.6801),  # Garvagh
            'BT52': (55.2073, -6.6301),  # Coleraine
            'BT53': (55.2773, -6.5301),  # Ballymoney
            'BT54': (55.2573, -6.3801),  # Ballycastle
            'BT55': (55.2373, -6.3301),  # Ballycastle
            'BT56': (55.1073, -6.4301),  # Armoy
            'BT57': (55.2973, -6.2301),  # Bushmills
            'BT58': (54.9173, -7.5801),  # Claudy
            'BT60': (54.6173, -6.4801),  # Armagh
            'BT61': (54.5773, -6.5301),  # Armagh
            'BT62': (54.4773, -6.4801),  # Craigavon
            'BT63': (54.4373, -6.4301),  # Craigavon
            'BT64': (54.4573, -6.3801),  # Craigavon
            'BT65': (54.4973, -6.3301),  # Craigavon
            'BT66': (54.4573, -6.4801),  # Cookstown
            'BT67': (54.4373, -6.5801),  # Cookstown
            'BT68': (54.6373, -6.7301),  # Dungannon
            'BT69': (54.5573, -6.7801),  # Dungannon
            'BT70': (54.5973, -6.8301),  # Dungannon
            'BT71': (54.5073, -6.8801),  # Dungannon
            'BT74': (54.3573, -7.6301),  # Enniskillen
            'BT75': (54.2973, -7.6801),  # Fivemiletown
            'BT76': (54.4173, -7.7301),  # Irvinestown
            'BT77': (54.5573, -7.4301),  # Augher
            'BT78': (54.4773, -7.4801),  # Omagh
            'BT79': (54.5173, -7.4801),  # Omagh
            'BT80': (54.7173, -7.2301),  # Cookstown
            'BT81': (54.7573, -7.1801),  # Castledawson
            'BT82': (54.5773, -7.6301),  # Omagh
            'BT92': (54.2573, -7.6301),  # Lisnaskea
            'BT93': (54.2173, -7.5801),  # Lisnaskea
            'BT94': (54.1773, -7.5301),  # Enniskillen
        }
    
    def _initialize_hospital_locations(self) -> Dict[str, Tuple[float, float]]:
        """初始化医院位置数据"""
        return {
            # 伦敦医院 - 与数据库名称匹配
            'Guy\'s and St Thomas\' NHS Foundation Trust': (51.5048, -0.0886),
            'King\'s College Hospital NHS Foundation Trust': (51.4685, -0.0981),
            'Imperial College Healthcare NHS Trust': (51.5177, -0.1735),
            'University College London Hospitals NHS Foundation Trust': (51.5214, -0.1365),
            'The Royal Marsden NHS Foundation Trust': (51.5214, -0.1570),
            'Royal Free London NHS Foundation Trust': (51.5549, -0.1687),
            'Barts Health NHS Trust': (51.5151, -0.0454),
            'Central and North West London NHS Foundation Trust': (51.5447, -0.1435),
            'Chelsea and Westminster Hospital NHS Foundation Trust': (51.4897, -0.1692),
            'The Whittington Hospital NHS Trust': (51.5642, -0.1403),
            'Moorfields Eye Hospital NHS Foundation Trust': (51.5225, -0.0875),
            'Great Ormond Street Hospital for Children NHS Foundation Trust': (51.5225, -0.1208),
            'Royal National Orthopaedic Hospital NHS Trust': (51.5642, -0.1403),
            'The Royal London Hospital': (51.5151, -0.0454),
            'St George\'s University Hospitals NHS Foundation Trust': (51.4274, -0.1733),
            'London North West University Healthcare NHS Trust': (51.5549, -0.3370),
            'Hillingdon Hospitals NHS Foundation Trust': (51.5447, -0.4760),
            'Epsom and St Helier University Hospitals NHS Trust': (51.3370, -0.2497),
            'Croydon Health Services NHS Trust': (51.3760, -0.0982),
            'Lewisham and Greenwich NHS Trust': (51.4629, 0.0077),
            'South London and Maudsley NHS Foundation Trust': (51.4685, -0.0981),
            'Oxleas NHS Foundation Trust': (51.4629, 0.0077),
            'Kingston Hospital NHS Foundation Trust': (51.4085, -0.2749),
            
            # 其他主要城市医院 - 与数据库名称匹配
            'Central Manchester University Hospitals NHS Foundation Trust': (53.4808, -2.2426),
            'Sheffield Teaching Hospitals NHS Foundation Trust': (53.3811, -1.4701),
            'Leeds Teaching Hospitals NHS Trust': (53.8008, -1.5491),
            'Newcastle upon Tyne Hospitals NHS Foundation Trust': (54.9783, -1.6178),
            'Cambridge University Hospitals NHS Foundation Trust': (52.2053, 0.1218),
            'Oxford University Hospitals NHS Foundation Trust': (51.7520, -1.2577),
            
            # 原有其他医院
            'Manchester University NHS Foundation Trust': (53.4808, -2.2426),
            'University Hospitals Birmingham NHS Foundation Trust': (52.4862, -1.8904),
            'The Leeds Teaching Hospitals NHS Trust': (53.8008, -1.5491),
            'Liverpool University Hospitals NHS Foundation Trust': (53.4084, -2.9916),
            'The Newcastle upon Tyne Hospitals NHS Foundation Trust': (54.9783, -1.6174),
            'University Hospitals Bristol and Weston NHS Foundation Trust': (51.4545, -2.5879),
            'Brighton and Sussex University Hospitals NHS Trust': (50.8225, -0.1372),
            
            # 苏格兰医院
            'NHS Lothian': (55.9533, -3.1883),
            'NHS Greater Glasgow and Clyde': (55.8642, -4.2518),
            
            # 威尔士医院
            'Cardiff and Vale University Health Board': (51.4816, -3.1791),
            'Swansea Bay University Health Board': (51.6214, -3.9436),
            
            # 北爱尔兰医院 - 添加与测试用户相关的医院
            'Belfast Health and Social Care Trust': (54.5973, -5.9301),
            'Northern Health and Social Care Trust': (54.8573, -6.2801),
            'South Eastern Health and Social Care Trust': (54.6173, -5.7301),
            'Southern Health and Social Care Trust': (54.3573, -6.3801),
            'Western Health and Social Care Trust': (54.8573, -7.4301),
            'Royal Victoria Hospital': (54.5984, -5.9378),
            'Belfast City Hospital': (54.5751, -5.9301),
            'Ulster Hospital': (54.5773, -5.8301),
            'Antrim Area Hospital': (54.7173, -6.2081),  # 接近用户位置BT37
            'Craigavon Area Hospital': (54.4473, -6.3801),
            'Altnagelvin Area Hospital': (55.0173, -7.3001),
            'Daisy Hill Hospital': (54.1773, -6.1801),
            'Erne Hospital': (54.3473, -7.6301),
        }
    
    def get_postcode_coordinates(self, postcode: str) -> Optional[Tuple[float, float]]:
        """获取邮编的坐标"""
        if not postcode:
            return None
            
        # 标准化邮编格式
        clean_postcode = postcode.replace(' ', '').upper()
        
        # 尝试匹配完整邮编前缀
        for length in [4, 3, 2, 1]:
            prefix = clean_postcode[:length]
            if prefix in self.postcode_coordinates:
                return self.postcode_coordinates[prefix]
        
        logger.warning(f"Unknown postcode: {postcode}")
        return None
    
    def get_hospital_coordinates(self, hospital_name: str) -> Optional[Tuple[float, float]]:
        """获取医院的坐标"""
        # 尝试精确匹配
        if hospital_name in self.hospital_locations:
            return self.hospital_locations[hospital_name]
        
        # 尝试模糊匹配
        for name, coords in self.hospital_locations.items():
            if hospital_name.lower() in name.lower() or name.lower() in hospital_name.lower():
                return coords
        
        logger.warning(f"Unknown hospital location: {hospital_name}")
        return None
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """使用Haversine公式计算两点间距离（公里）"""
        # 地球半径（公里）
        R = 6371.0
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 计算差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine公式
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return round(distance, 1)
    
    def calculate_distance_between_postcodes(self, postcode1: str, postcode2: str) -> Optional[float]:
        """计算两个邮编之间的距离"""
        coords1 = self.get_postcode_coordinates(postcode1)
        coords2 = self.get_postcode_coordinates(postcode2)
        
        if not coords1 or not coords2:
            return None
        
        return self.calculate_distance(coords1[0], coords1[1], coords2[0], coords2[1])
    
    def calculate_hospital_distance(self, user_postcode: str, hospital_name: str) -> Optional[float]:
        """计算用户邮编到医院的距离"""
        user_coords = self.get_postcode_coordinates(user_postcode)
        hospital_coords = self.get_hospital_coordinates(hospital_name)
        
        if not user_coords or not hospital_coords:
            return None
        
        return self.calculate_distance(user_coords[0], user_coords[1], hospital_coords[0], hospital_coords[1])
    
    def filter_hospitals_by_distance(self, user_postcode: str, hospital_data: List[Dict], 
                                   max_distance_km: int) -> List[Dict]:
        """根据距离过滤医院数据"""
        filtered_hospitals = []
        
        for hospital in hospital_data:
            hospital_name = hospital.get('provider_name', hospital.get('org_name', hospital.get('hospital_name', '')))
            
            distance = self.calculate_hospital_distance(user_postcode, hospital_name)
            
            # 添加距离信息
            hospital_copy = hospital.copy()
            hospital_copy['distance_km'] = distance
            
            # 如果无法计算距离，给予一个默认距离（保守估计）
            if distance is None:
                hospital_copy['distance_km'] = max_distance_km * 0.8  # 稍微保守一些
                filtered_hospitals.append(hospital_copy)
                logger.warning(f"Could not calculate distance for {hospital_name}, using default")
            elif distance <= max_distance_km:
                filtered_hospitals.append(hospital_copy)
        
        # 按距离排序
        filtered_hospitals.sort(key=lambda x: x.get('distance_km', float('inf')))
        
        return filtered_hospitals
    
    def get_nearby_hospitals_from_db(self, user_postcode: str, specialty: str, 
                                   max_distance_km: int, db_path: str = None) -> List[Dict]:
        """从数据库获取附近医院数据"""
        if not db_path:
            db_path = self.db_path
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取所有相关专科的医院数据
            cursor.execute('''
            SELECT DISTINCT org_name, specialty_name, waiting_time_weeks, patient_count
            FROM nhs_rtt_data 
            WHERE specialty_name LIKE ?
            ORDER BY waiting_time_weeks ASC
            ''', (f'%{specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            hospital_data = []
            for row in rows:
                hospital_data.append({
                    'org_name': row[0],
                    'provider_name': row[0],
                    'hospital_name': row[0],
                    'specialty_name': row[1],
                    'waiting_time_weeks': row[2],
                    'waiting_weeks': row[2],
                    'patient_count': row[3],
                    'patients_waiting': row[3]
                })
            
            # 根据距离过滤
            filtered_hospitals = self.filter_hospitals_by_distance(
                user_postcode, hospital_data, max_distance_km
            )
            
            return filtered_hospitals
            
        except Exception as e:
            logger.error(f"获取附近医院数据失败: {e}")
            return []
    
    def add_distance_info_to_trends(self, user_postcode: str, trend_data: List, 
                                  max_distance_km: int) -> Tuple[List, List]:
        """为趋势数据添加距离信息并分为范围内和范围外"""
        within_range = []
        outside_range = []
        
        for trend in trend_data:
            hospital_name = getattr(trend, 'hospital_name', '')
            distance = self.calculate_hospital_distance(user_postcode, hospital_name)
            
            # 为trend对象添加distance属性
            trend.distance_km = distance
            
            if distance is None:
                # 无法计算距离的医院，保守地放在范围外
                outside_range.append(trend)
            elif distance <= max_distance_km:
                within_range.append(trend)
            else:
                outside_range.append(trend)
        
        # 分别按等待时间排序
        within_range.sort(key=lambda x: x.current_weeks)
        outside_range.sort(key=lambda x: x.current_weeks)
        
        return within_range, outside_range 