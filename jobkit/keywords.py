"""Keyword dictionary shared by ranking, ATS scoring and the honesty check.

canonical name -> case-insensitive regex. It spans software, data/ML, general
engineering and robotics/embedded so one kit serves many fields. Add terms for
your field here (see CONTRIBUTING.md); every term you add is automatically also
policed by the honesty check.
"""
import re

HARD = {
    # languages
    "Python": r"\bpython\b", "Java": r"\bjava\b", "C++": r"c\+\+|\bcpp\b", "C#": r"\bc#|\.net\b|\bdotnet\b",
    "C": r"(?<![\w+#.])c(?![\w+#])(?=\s*(,|/|and\b|programming|language))|\bembedded c\b",
    "Go": r"\bgolang\b|\bgo\b(?= (language|programming|services|microservices))", "Rust": r"\brust\b",
    "JavaScript": r"javascript|\bnode\.?js\b", "TypeScript": r"typescript", "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b", "Scala": r"\bscala\b", "Ruby": r"\bruby\b|\brails\b", "PHP": r"\bphp\b",
    "R": r"(?<![\w-])r(?![\w-])(?=\s*(,|/|and\b|programming|studio|language))|\brstudio\b",
    "SQL": r"\bsql\b|postgres|mysql|sqlite", "Bash": r"\bbash\b|shell script", "MATLAB": r"\bmatlab\b",
    "Simulink": r"simulink", "VHDL": r"\bvhdl\b", "Verilog": r"verilog|systemverilog", "LabVIEW": r"labview",
    # web / backend / cloud
    "React": r"\breact\b", "Angular": r"\bangular\b", "Vue": r"\bvue\b", "HTML/CSS": r"\bhtml\b|\bcss\b",
    "REST API": r"\brest(ful)?\b|\bapis?\b", "GraphQL": r"graphql", "gRPC": r"\bgrpc\b",
    "microservices": r"microservice", "distributed systems": r"distributed system",
    "AWS": r"\baws\b|amazon web services|\bec2\b|\bs3\b|lambda", "GCP": r"\bgcp\b|google cloud",
    "Azure": r"\bazure\b", "cloud": r"\bcloud\b", "Docker": r"docker|container",
    "Kubernetes": r"kubernetes|\bk8s\b", "Terraform": r"terraform", "Linux": r"linux|ubuntu|unix",
    "Git": r"\bgit\b|github|gitlab", "CI/CD": r"ci/cd|continuous integration|github actions|jenkins|circleci",
    "Kafka": r"\bkafka\b", "Redis": r"\bredis\b", "MongoDB": r"mongodb", "NoSQL": r"nosql|dynamodb|cassandra",
    "Spark": r"\bspark\b|pyspark", "Airflow": r"airflow", "dbt": r"\bdbt\b", "Snowflake": r"snowflake",
    "data pipelines": r"data pipeline|\betl\b|\belt\b", "data structures": r"data structure",
    "algorithms": r"algorithm", "object-oriented design": r"object[- ]oriented|\boop\b",
    "system design": r"system design|software architecture", "multithreading": r"multithread|concurren",
    "testing": r"\btest(s|ing|ed)?\b", "unit tests": r"unit test|pytest|junit|gtest|googletest",
    "debugging": r"debug|troubleshoot|root[- ]cause", "security": r"\bsecurity\b|\bsecure\b",
    "mobile": r"\bios\b|\bandroid\b|mobile app",
    # data / ML
    "machine learning": r"machine learning|\bml\b", "deep learning": r"deep learning|neural net",
    "PyTorch": r"pytorch", "TensorFlow": r"tensorflow|keras", "scikit-learn": r"scikit|sklearn",
    "pandas": r"\bpandas\b", "NumPy": r"numpy", "statistics": r"statistic", "A/B testing": r"a/b test|experimentation",
    "NLP": r"\bnlp\b|natural language", "LLM": r"\bllms?\b|large language model", "computer vision": r"computer vision|opencv",
    "data analysis": r"data analy|analytics", "data visualization": r"visuali[sz]ation|tableau|power bi|looker",
    "Tableau": r"tableau", "Excel": r"\bexcel\b", "MLOps": r"mlops|model deployment|model serving",
    # engineering (mech / electrical / industrial / civil)
    "CAD": r"\bcad\b", "SolidWorks": r"solidworks", "AutoCAD": r"autocad", "Fusion 360": r"fusion 360",
    "CATIA": r"\bcatia\b", "Creo": r"\bcreo\b", "NX": r"siemens nx|\bnx\b(?= cad)", "Revit": r"\brevit\b",
    "Civil 3D": r"civil 3d", "GD&T": r"gd&t|geometric dimensioning", "FEA": r"\bfea\b|finite element|ansys|abaqus",
    "CFD": r"\bcfd\b|computational fluid", "thermal analysis": r"thermal (analysis|management|design)|heat transfer",
    "DFM": r"\bdfm\b|design for manufactur", "manufacturing": r"manufactur", "machining": r"machining|\bcnc\b",
    "3D printing": r"3d print|additive manufactur", "injection molding": r"injection mold",
    "sheet metal": r"sheet metal", "tolerance analysis": r"tolerance (analysis|stack)",
    "lean": r"\blean\b|six sigma|kaizen|\b5s\b", "process improvement": r"process improvement|continuous improvement",
    "supply chain": r"supply chain|logistics|inventory", "quality": r"\bquality\b|\bqa\b|\bqc\b|\bspc\b",
    "root cause analysis": r"root cause analysis|\brca\b|8d|fmea", "PLC": r"\bplc\b|ladder logic",
    "SCADA": r"scada", "circuit design": r"circuit design|schematic", "PCB": r"\bpcb\b|altium|kicad|eagle",
    "power electronics": r"power electronic|inverter|converter", "power systems": r"power system|power distribution|grid",
    "electronics": r"electronic|oscilloscope|multimeter", "signal processing": r"signal processing|\bdsp\b",
    "structural analysis": r"structural (analysis|design|engineering)", "geotechnical": r"geotechnical",
    "transportation engineering": r"transportation engineering|traffic", "surveying": r"surveying|\bgis\b",
    "construction": r"construction", "project management": r"project management|\bpmp\b|schedul",
    "HVAC": r"\bhvac\b", "batteries": r"batter(y|ies)|\bcells?\b(?= (chemistry|testing))",
    # robotics / embedded / controls
    "ROS": r"\bros ?2?\b", "embedded": r"embedded", "firmware": r"firmware", "microcontrollers": r"microcontroller|\bmcu\b|stm32|esp32|arduino",
    "RTOS": r"\brtos\b|freertos|zephyr", "CAN": r"\bcan ?bus\b|\bcanbus\b", "I2C/SPI/UART": r"\bi2c\b|\bspi\b|\buart\b",
    "controls": r"control (system|loop|theory|engineering)|controls engineer", "PID": r"\bpid\b",
    "MPC": r"\bmpc\b|model predictive", "kinematics": r"kinematic", "manipulation": r"manipulat(ion|or)",
    "motion planning": r"motion planning|path planning", "SLAM": r"\bslam\b", "localization": r"locali[sz]ation",
    "sensor fusion": r"sensor fusion", "Kalman filter": r"kalman|\bekf\b", "perception": r"\bperception\b",
    "simulation": r"simulat", "Gazebo": r"gazebo", "LiDAR": r"lidar", "robotics": r"robot",
    "autonomy": r"autonom", "HIL": r"\bhil\b|hardware[- ]in[- ]the[- ]loop", "drones": r"\bdrones?\b|\buavs?\b",
}

SOFT = {
    "communication": r"communicat", "collaboration": r"collaborat|teamwork", "cross-functional": r"cross[- ]functional",
    "leadership": r"\blead(ership)?\b|\bled\b", "mentoring": r"mentor", "ownership": r"\bownership\b",
    "problem solving": r"problem[- ]solv", "documentation": r"document", "detail-oriented": r"detail[- ]oriented|attention to detail",
}

# Umbrella terms nearly every JD in a field hits; they carry little signal.
LIGHT = {"testing", "cloud", "robotics", "debugging", "quality", "manufacturing", "construction", "C", "R"}


def has(rx: str, text: str) -> bool:
    return re.search(rx, text or "", re.I) is not None


def found(text: str, table: dict = HARD) -> set[str]:
    return {k for k, rx in table.items() if has(rx, text)}
