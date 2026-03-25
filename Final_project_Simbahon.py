import tkinter as tk
from tkinter import ttk, messagebox
from abc import ABC, abstractmethod
import sqlite3
import hashlib
import math
import random
import os
import datetime

class AuthenticationError(Exception):
    pass

class VehicleCapacityError(Exception):
    pass

class LocationNotFoundError(Exception):
    pass

class DatabaseError(Exception):
    pass
class Location:
    VALID_TYPES = ("City", "Municipality", "Barangay", "Landmark")

    def __init__(self, name: str, lat: float, lon: float, loc_type: str):
        self.__name     = name
        self.__lat      = lat
        self.__lon      = lon
        self.__loc_type = loc_type
        self._validate()

    def _validate(self):
        if not (-90 <= self.__lat <= 90):
            raise ValueError(f"Invalid latitude: {self.__lat}")
        if not (-180 <= self.__lon <= 180):
            raise ValueError(f"Invalid longitude: {self.__lon}")
        if self.__loc_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid type: {self.__loc_type}")

    @property
    def name(self):     return self.__name
    @property
    def lat(self):      return self.__lat
    @property
    def lon(self):      return self.__lon
    @property
    def loc_type(self): return self.__loc_type

    def distance_to(self, other: "Location") -> float:
      
        R = 6371.0
        p1, p2 = math.radians(self.__lat),  math.radians(other.__lat)
        dp     = math.radians(other.__lat  - self.__lat)
        dl     = math.radians(other.__lon  - self.__lon)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def __str__(self):
        return f"{self.__name} ({self.__loc_type})"

    def __repr__(self):
        return f"Location('{self.__name}', {self.__lat}, {self.__lon})"

class Vehicle(ABC):
    _id_counter = 0

    def __init__(self, origin: Location, destination: Location):
        Vehicle._id_counter += 1
        self._id          = f"V{Vehicle._id_counter:03d}"
        self._origin      = origin
        self._destination = destination
        self.__passengers = random.randint(0, self.capacity // 2)
        self._progress    = random.uniform(0.0, 1.0)  
        self._direction   = 1
        self._active      = True
 
    @abstractmethod
    def get_icon(self) -> str:
        pass

    @abstractmethod
    def get_speed(self) -> float:
        pass

    @abstractmethod
    def get_avg_kmh(self) -> int:
        pass

    @property
    @abstractmethod
    def capacity(self) -> int:
        pass

    @property
    @abstractmethod
    def vehicle_type(self) -> str:
        pass
    @property
    def id(self):           return self._id
    @property
    def origin(self):       return self._origin
    @property
    def destination(self):  return self._destination
    @property
    def active(self):       return self._active

    @property
    def passengers(self) -> int:
        return self.__passengers

    @passengers.setter
    def passengers(self, value: int):
        if value < 0:
            raise VehicleCapacityError("Passengers cannot be negative.")
        if value > self.capacity:
            raise VehicleCapacityError(
                f"{self.vehicle_type} capacity is {self.capacity}. Got {value}.")
        self.__passengers = value

    @property
    def occupancy_pct(self) -> float:
        return self.__passengers / self.capacity

    @property
    def is_full(self) -> bool:
        return self.__passengers >= self.capacity

    @property
    def status(self) -> str:
        if self.is_full:           return "FULL"
        if self.occupancy_pct > 0.75: return "BUSY"
        return "OK"

    @property
    def current_lat(self) -> float:
        return (self._origin.lat +
                (self._destination.lat - self._origin.lat) * self._progress)

    @property
    def current_lon(self) -> float:
        return (self._origin.lon +
                (self._destination.lon - self._origin.lon) * self._progress)

    @property
    def route_km(self) -> float:
        return self._origin.distance_to(self._destination)

    @property
    def eta_minutes(self) -> int:
        remaining = self.route_km * (1 - self._progress)
        return max(1, int((remaining / self.get_avg_kmh()) * 60))

    def tick(self):
        self._progress += self.get_speed() * self._direction
        if self._progress >= 1.0:
            self._progress  = 1.0
            self._direction = -1
            self.passengers = random.randint(0, self.capacity // 2)
        elif self._progress <= 0.0:
            self._progress  = 0.0
            self._direction = 1
            self.passengers = random.randint(0, self.capacity)
        if random.random() < 0.12:
            try:
                self.passengers = max(0, min(
                    self.capacity,
                    self.__passengers + random.randint(-2, 2)
                ))
            except VehicleCapacityError:
                pass

    def get_info(self) -> dict:
        return {
            "ID":         self._id,
            "Type":       self.vehicle_type,
            "From":       self._origin.name,
            "To":         self._destination.name,
            "Passengers": f"{self.passengers}/{self.capacity}",
            "ETA":        f"~{self.eta_minutes} min",
            "Status":     self.status,
            "Route km":   f"{self.route_km:.2f} km",
        }

    def __str__(self):
        return (f"{self.get_icon()} {self._id} | {self.vehicle_type} | "
                f"{self._origin.name} → {self._destination.name} | "
                f"{self.passengers}/{self.capacity}")
class Jeepney(Vehicle):
    def __init__(self, origin: Location, destination: Location):
        super().__init__(origin, destination)

    @property
    def capacity(self) -> int:     return 18
    @property
    def vehicle_type(self) -> str: return "Jeepney"

    def get_icon(self) -> str:     return "🚐"
    def get_speed(self) -> float:  return 0.008
    def get_avg_kmh(self) -> int:  return 35

    def get_info(self) -> dict:
        info = super().get_info()
        info["Note"] = "Fixed route, flag stop allowed"
        return info


class Multicab(Vehicle):
    def __init__(self, origin: Location, destination: Location):
        super().__init__(origin, destination)

    @property
    def capacity(self) -> int:     return 12
    @property
    def vehicle_type(self) -> str: return "Multicab"

    def get_icon(self) -> str:     return "🚌"
    def get_speed(self) -> float:  return 0.010
    def get_avg_kmh(self) -> int:  return 40

    def get_info(self) -> dict:
        info = super().get_info()
        info["Note"] = "Flexible route, barangay coverage"
        return info


class Bus(Vehicle):
   
    def __init__(self, origin: Location, destination: Location):
        super().__init__(origin, destination)

    @property
    def capacity(self) -> int:     return 50
    @property
    def vehicle_type(self) -> str: return "Bus"

    def get_icon(self) -> str:     return "🚍"
    def get_speed(self) -> float:  return 0.014
    def get_avg_kmh(self) -> int:  return 60

    def get_info(self) -> dict:
        info = super().get_info()
        info["Note"] = "Inter-city / provincial route"
        return info

class User:
    ROLES = ("passenger", "admin")

    def __init__(self, username: str, password_plain: str, role: str = "passenger"):
        self.__username      = username.strip().lower()
        self.__password_hash = self._hash(password_plain)
        self.__role          = role if role in self.ROLES else "passenger"
        self.__login_time    = None

    @staticmethod
    def _hash(plain: str) -> str:
        return hashlib.sha256(plain.encode()).hexdigest()

    def authenticate(self, password_plain: str) -> bool:
        return self.__password_hash == self._hash(password_plain)

    def login(self):
        self.__login_time = datetime.datetime.now()

    @property
    def username(self):   return self.__username
    @property
    def role(self):       return self.__role
    @property
    def is_admin(self):   return self.__role == "admin"
    @property
    def login_time(self): return self.__login_time

    def __str__(self):
        return f"User({self.__username}, role={self.__role})"
class Booking:

    _booking_counter = 0

    def __init__(self, user: User, vehicle: Vehicle, pickup: Location):
        Booking._booking_counter += 1
        self.__booking_id  = f"BK{Booking._booking_counter:04d}"
        self.__user        = user
        self.__vehicle     = vehicle
        self.__pickup      = pickup
        self.__timestamp   = datetime.datetime.now()
        self.__status      = "Confirmed"

    @property
    def booking_id(self):  return self.__booking_id
    @property
    def user(self):        return self.__user
    @property
    def vehicle(self):     return self.__vehicle
    @property
    def pickup(self):      return self.__pickup
    @property
    def timestamp(self):   return self.__timestamp
    @property
    def status(self):      return self.__status

    def cancel(self):
        self.__status = "Cancelled"

    def __str__(self):
        return (f"Booking {self.__booking_id} | {self.__user.username} | "
                f"{self.__vehicle.id} | {self.__pickup.name} | {self.__status}")

class Database:
    
    DB_FILE = "commuters_tracking.db"

    def __init__(self):
        try:
            self._conn = sqlite3.connect(self.DB_FILE)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()
            self._seed_defaults()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                role          TEXT    DEFAULT 'passenger',
                created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS locations (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT    UNIQUE NOT NULL,
                lat      REAL    NOT NULL,
                lon      REAL    NOT NULL,
                loc_type TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id  TEXT NOT NULL,
                username    TEXT NOT NULL,
                vehicle_id  TEXT NOT NULL,
                pickup      TEXT NOT NULL,
                status      TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vehicle_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id  TEXT NOT NULL,
                v_type      TEXT NOT NULL,
                origin      TEXT NOT NULL,
                destination TEXT NOT NULL,
                passengers  INTEGER,
                logged_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._conn.commit()

    def _seed_defaults(self):
        cur = self._conn.cursor()

        # Default users
        defaults = [
            ("simbahon",  "pass123",  "passenger"),
            ("dryan", "pass456",  "passenger"),
            ("kyle", "pass789",  "passenger"),
            ("admin", "admin123", "admin"),
        ]
        for uname, pwd, role in defaults:
            h = hashlib.sha256(pwd.encode()).hexdigest()
            cur.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) "
                "VALUES (?,?,?)", (uname, h, role))

        # Default locations
        locs = [
            ("Placer",                9.6167,  125.5833, "Municipality"),
            ("Claver",                9.5833,  125.7167, "Municipality"),
            ("Malimono",              9.6167,  125.4000, "Municipality"),
            ("Kitcharao",             9.4333,  125.5667, "Municipality"),
            ("Bacuag",                9.6667,  125.6500, "Municipality"),
            ("Tagana-an",             9.7167,  125.6000, "Municipality"),
            ("Tubod",                 9.7500,  125.5167, "Municipality"),
            ("Cantilan",              9.3167,  125.9833, "Municipality"),
            ("Sison",                 9.5000,  125.5167, "Municipality"),
            ("Mainit",                9.5333,  125.5333, "Municipality"),
            ("Butuan City",           8.9492,  125.5436, "City"),
            ("Surigao City",          9.7845,  125.4950, "City"),
            ("Ampayon",               8.9700,  125.5950, "Barangay"),
            ("Punta Bilar",           9.7950,  125.5150, "Barangay"),
            ("Serna",                 9.7700,  125.5050, "Barangay"),
            ("Bad-as",                9.6500,  125.6200, "Barangay"),
            ("Pier 2 (Pantalan 2)",   9.7880,  125.5020, "Landmark"),
            ("Terminal (Brgy Luna)",  9.7760,  125.4880, "Landmark"),
        ]
        for name, lat, lon, t in locs:
            cur.execute(
                "INSERT OR IGNORE INTO locations (name, lat, lon, loc_type) "
                "VALUES (?,?,?,?)", (name, lat, lon, t))

        self._conn.commit()

    def get_user(self, username: str):
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?",
                    (username.lower(),))
        return cur.fetchone()

    def add_user(self, username: str, password: str, role: str = "passenger"):
        try:
            h = hashlib.sha256(password.encode()).hexdigest()
            self._conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                (username.lower(), h, role))
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise DatabaseError(f"Username '{username}' already exists.")

    def get_all_locations(self) -> list:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM locations ORDER BY loc_type, name")
        return cur.fetchall()

    def save_booking(self, booking: Booking):
        self._conn.execute(
            "INSERT INTO bookings (booking_id, username, vehicle_id, pickup, status) "
            "VALUES (?,?,?,?,?)",
            (booking.booking_id, booking.user.username,
             booking.vehicle.id, booking.pickup.name, booking.status))
        self._conn.commit()

    def get_bookings(self, username: str = None) -> list:
        cur = self._conn.cursor()
        if username:
            cur.execute(
                "SELECT * FROM bookings WHERE username=? ORDER BY created_at DESC",
                (username,))
        else:
            cur.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        return cur.fetchall()

    def log_vehicle(self, v: Vehicle):
        self._conn.execute(
            "INSERT INTO vehicle_log (vehicle_id, v_type, origin, destination, passengers) "
            "VALUES (?,?,?,?,?)",
            (v.id, v.vehicle_type, v.origin.name, v.destination.name, v.passengers))
        self._conn.commit()

    def close(self):
        self._conn.close()

class AppController:

    ROUTE_DEFS = [
        ("Terminal (Brgy Luna)", "Surigao City",        Jeepney),
        ("Terminal (Brgy Luna)", "Placer",               Jeepney),
        ("Terminal (Brgy Luna)", "Sison",                Jeepney),
        ("Terminal (Brgy Luna)", "Mainit",               Jeepney),
        ("Terminal (Brgy Luna)", "Claver",               Multicab),
        ("Terminal (Brgy Luna)", "Tagana-an",            Multicab),
        ("Terminal (Brgy Luna)", "Bad-as",               Multicab),
        ("Pier 2 (Pantalan 2)",  "Punta Bilar",          Jeepney),
        ("Pier 2 (Pantalan 2)",  "Serna",                Jeepney),
        ("Pier 2 (Pantalan 2)",  "Terminal (Brgy Luna)", Multicab),
        ("Surigao City",         "Butuan City",          Bus),
        ("Surigao City",         "Tubod",                Jeepney),
        ("Surigao City",         "Bacuag",               Jeepney),
        ("Surigao City",         "Malimono",             Jeepney),
        ("Surigao City",         "Kitcharao",            Bus),
        ("Surigao City",         "Cantilan",             Bus),
        ("Butuan City",          "Ampayon",              Jeepney),
        ("Surigao City",         "Tagana-an",            Multicab),
    ]

    def __init__(self):
        self._db           = Database()
        self._locations    = self._load_locations()
        self._fleet        = self._init_fleet()
        self._current_user = None
        self._bookings     = []

    def _load_locations(self) -> dict:
        locs = {}
        for row in self._db.get_all_locations():
            locs[row["name"]] = Location(
                row["name"], row["lat"], row["lon"], row["loc_type"])
        return locs

    def _init_fleet(self) -> list:
        fleet = []
        for orig, dest, cls in self.ROUTE_DEFS:
            try:
                o = self._locations[orig]
                d = self._locations[dest]
                fleet.append(cls(o, d))
            except KeyError as e:
                print(f"[WARNING] Location not found: {e}")
        return fleet

    def login(self, username: str, password: str) -> User:
        row = self._db.get_user(username)
        if not row:
            raise AuthenticationError("Username not found.")
        h = hashlib.sha256(password.encode()).hexdigest()
        if row["password_hash"] != h:
            raise AuthenticationError("Incorrect password.")
        u = User.__new__(User)
        u._User__username      = row["username"]
        u._User__password_hash = row["password_hash"]
        u._User__role          = row["role"]
        u._User__login_time    = datetime.datetime.now()
        self._current_user = u
        return u

    def register(self, username: str, password: str):
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters.")
        self._db.add_user(username, password)

    def logout(self):
        self._current_user = None

    def tick_fleet(self):
        for v in self._fleet:
            v.tick()

    def get_fleet(self, vtype_filter: str = "All") -> list:
        if vtype_filter == "All":
            return list(self._fleet)
        return [v for v in self._fleet if v.vehicle_type == vtype_filter]
    
    def book_vehicle(self, vehicle_id: str, pickup_name: str) -> Booking:
        if not self._current_user:
            raise AuthenticationError("Must be logged in to book.")
        vehicle = next((v for v in self._fleet if v.id == vehicle_id), None)
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found.")
        if vehicle.is_full:
            raise VehicleCapacityError(
                f"{vehicle.vehicle_type} {vehicle_id} is full.")
        if pickup_name not in self._locations:
            raise LocationNotFoundError(f"'{pickup_name}' not found.")
        pickup  = self._locations[pickup_name]
        booking = Booking(self._current_user, vehicle, pickup)
        self._bookings.append(booking)
        self._db.save_booking(booking)
        return booking

    def get_my_bookings(self) -> list:
        if not self._current_user:
            return []
        return self._db.get_bookings(self._current_user.username)

    def get_all_bookings(self) -> list:
        return self._db.get_bookings()

    def all_to_surigao(self) -> list:
        surigao = self._locations["Surigao City"]
        results = []
        for name, loc in self._locations.items():
            if name == "Surigao City":
                continue
            km = loc.distance_to(surigao)
            results.append((name, loc.loc_type, round(km, 2)))
        return sorted(results, key=lambda x: x[2])

    def distances_to(self, dest_name: str, origins: list) -> list:
        if dest_name not in self._locations:
            raise LocationNotFoundError(dest_name)
        dest    = self._locations[dest_name]
        results = []
        for o in origins:
            if o in self._locations and o != dest_name:
                km = self._locations[o].distance_to(dest)
                results.append((o, round(km, 2)))
        return sorted(results, key=lambda x: x[1])

    @property
    def locations(self): return self._locations
    @property
    def current_user(self): return self._current_user

    def close(self):
        self._db.close()

BG      = "#0B1120"
BG2     = "#111D30"
CARD    = "#182540"
CARD2   = "#1E2F50"
ACCENT  = "#00C9FF"
GREEN   = "#38EF7D"
ORANGE  = "#FF8C42"
RED     = "#FF3B3B"
GOLD    = "#FFD700"
WHITE   = "#FFFFFF"
DIM     = "#5C7A9A"
FBG     = ("Segoe UI", 22, "bold")
FH      = ("Segoe UI", 12, "bold")
FN      = ("Segoe UI", 10)
FS      = ("Segoe UI",  9)
FC      = ("Courier New", 9)

VCOLOR  = {"Jeepney": GOLD, "Multicab": GREEN, "Bus": ACCENT}
LCOLOR  = {"City": GOLD, "Municipality": DIM,
           "Barangay": "#88AACC", "Landmark": ORANGE}

LAT_MIN, LAT_MAX = 8.88, 9.90
LON_MIN, LON_MAX = 125.35, 126.05


def latlon_xy(lat, lon, W, H, pad=28):
    x = pad + (lon - LON_MIN) / (LON_MAX - LON_MIN) * (W - 2*pad)
    y = pad + (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (H - 2*pad)
    return int(x), int(y)

class AppView(tk.Tk):
    
    def __init__(self, ctrl: AppController):
        super().__init__()
        self._ctrl    = ctrl
        self._running = True
        self._filter  = tk.StringVar(value="All")
        self._tab     = "Map"

        self.title("Commuters Transportation Tracking System — Surigao del Norte")
        self.geometry("1220x760")
        self.minsize(1100, 680)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._show_login()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _style_treeview(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("Treeview",
                    background=CARD, foreground=WHITE,
                    fieldbackground=CARD, rowheight=25,
                    font=("Segoe UI", 9))
        s.configure("Treeview.Heading",
                    background=BG2, foreground=ACCENT,
                    font=("Segoe UI", 9, "bold"))
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])
        s.configure("TNotebook",      background=BG2, borderwidth=0)
        s.configure("TNotebook.Tab",  background=CARD, foreground=WHITE,
                    padding=[12, 6], font=("Segoe UI", 9))
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])

    def _show_login(self):
        self._clear()
        self._style_treeview()

        wrap = tk.Frame(self, bg=BG)
        wrap.place(relx=.5, rely=.5, anchor="center")

        tk.Label(wrap, text="🚌", font=("Segoe UI", 52),
                 bg=BG, fg=ACCENT).pack()
        tk.Label(wrap, text="Commuters Tracking System",
                 font=FBG, bg=BG, fg=WHITE).pack(pady=(0, 4))
        tk.Label(wrap, text="St. Paul University Surigao  ·  Surigao del Norte",
                 font=FN, bg=BG, fg=DIM).pack(pady=(0, 20))

        card = tk.Frame(wrap, bg=BG2, padx=44, pady=34)
        card.pack()

        # Tabs: Login / Register
        self._auth_tab = tk.StringVar(value="login")
        tab_row = tk.Frame(card, bg=BG2)
        tab_row.pack(fill="x", pady=(0, 18))
        for lbl, val in [("Sign In", "login"), ("Register", "register")]:
            tk.Button(tab_row, text=lbl, font=FN,
                      bg=ACCENT if val == "login" else CARD,
                      fg=BG if val == "login" else WHITE,
                      relief="flat", cursor="hand2", width=12,
                      command=lambda v=val: self._switch_auth(v)
                      ).pack(side="left", padx=3, ipady=5)

        self._auth_body = tk.Frame(card, bg=BG2)
        self._auth_body.pack()
        self._build_login_form()

        tk.Label(wrap,
                 text="Demo: simbahon/pass123  ·  dryan/pass456  ·  kyle/pass789",
                 font=("Segoe UI", 8), bg=BG, fg=DIM).pack(pady=(14, 0))

    def _switch_auth(self, tab):
        self._auth_tab.set(tab)
        self._show_login()

    def _build_login_form(self):
        for w in self._auth_body.winfo_children():
            w.destroy()
        f = self._auth_body

        tk.Label(f, text="Username", font=FS, bg=BG2, fg=DIM).pack(anchor="w")
        self._eu = tk.Entry(f, font=FN, bg=CARD, fg=WHITE,
                            insertbackground=WHITE, relief="flat", width=28)
        self._eu.pack(pady=(2, 12), ipady=7)

        tk.Label(f, text="Password", font=FS, bg=BG2, fg=DIM).pack(anchor="w")
        self._ep = tk.Entry(f, font=FN, bg=CARD, fg=WHITE,
                            insertbackground=WHITE, show="●",
                            relief="flat", width=28)
        self._ep.pack(pady=(2, 6), ipady=7)

        self._err_lbl = tk.Label(f, text="", font=FS, bg=BG2, fg=RED)
        self._err_lbl.pack()

        tk.Button(f, text="SIGN IN", font=FH,
                  bg=ACCENT, fg=BG, relief="flat",
                  activebackground="#009FCC", cursor="hand2",
                  width=24, command=self._do_login
                  ).pack(pady=(10, 0), ipady=7)

        self._eu.focus()
        self._ep.bind("<Return>", lambda e: self._do_login())

    def _build_register_form(self):
        for w in self._auth_body.winfo_children():
            w.destroy()
        f = self._auth_body

        for lbl, attr, show in [
            ("New Username", "_ru", ""),
            ("Password",     "_rp", "●"),
            ("Confirm",      "_rc", "●"),
        ]:
            tk.Label(f, text=lbl, font=FS, bg=BG2, fg=DIM).pack(anchor="w")
            e = tk.Entry(f, font=FN, bg=CARD, fg=WHITE,
                         insertbackground=WHITE, show=show,
                         relief="flat", width=28)
            e.pack(pady=(2, 10), ipady=7)
            setattr(self, attr, e)

        self._err_lbl = tk.Label(f, text="", font=FS, bg=BG2, fg=RED)
        self._err_lbl.pack()

        tk.Button(f, text="REGISTER", font=FH,
                  bg=GREEN, fg=BG, relief="flat",
                  cursor="hand2", width=24,
                  command=self._do_register
                  ).pack(pady=(8, 0), ipady=7)

    def _do_login(self):
        try:
            u = self._eu.get().strip()
            p = self._ep.get()
            if not u or not p:
                raise ValueError("Please fill in all fields.")
            self._ctrl.login(u, p)
            self._show_main()
        except (AuthenticationError, ValueError) as e:
            self._err_lbl.config(text=str(e))

    def _do_register(self):
        try:
            u  = self._ru.get().strip()
            p  = self._rp.get()
            p2 = self._rc.get()
            if not u or not p:
                raise ValueError("Please fill in all fields.")
            if p != p2:
                raise ValueError("Passwords do not match.")
            self._ctrl.register(u, p)
            messagebox.showinfo("Success",
                                f"Account '{u}' created!\nYou can now sign in.")
            self._switch_auth("login")
        except (ValueError, DatabaseError) as e:
            self._err_lbl.config(text=str(e))

    def _show_main(self):
        self._clear()
        user = self._ctrl.current_user

        top = tk.Frame(self, bg=BG2, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top,
                 text="🚌  Commuters Transportation Tracking System",
                 font=FH, bg=BG2, fg=ACCENT).pack(side="left", padx=16)
        tk.Button(top, text="Logout", font=FS, bg=RED, fg=WHITE,
                  relief="flat", cursor="hand2",
                  command=self._logout).pack(side="right", padx=10)
        role_col = ORANGE if user.is_admin else GREEN
        tk.Label(top, text=f"👤 {user.username}  [{user.role}]",
                 font=FN, bg=BG2, fg=role_col).pack(side="right", padx=6)

        tabs = ["🗺️ Map", "📊 Distances", "📋 Vehicles", "🎫 My Bookings"]
        if user.is_admin:
            tabs.append("🔧 Admin")
        tab_bar = tk.Frame(self, bg=BG, pady=5)
        tab_bar.pack(fill="x", padx=10)
        self._tab_btns = {}
        keys = ["Map", "Distances", "Vehicles", "Bookings", "Admin"]
        for i, (label, key) in enumerate(zip(tabs, keys[:len(tabs)])):
            b = tk.Button(tab_bar, text=label, font=FN,
                          bg=ACCENT if key == "Map" else CARD,
                          fg=BG    if key == "Map" else WHITE,
                          relief="flat", cursor="hand2",
                          padx=12, pady=5,
                          command=lambda k=key: self._switch_tab(k))
            b.pack(side="left", padx=3)
            self._tab_btns[key] = b

        self._content = tk.Frame(self, bg=BG)
        self._content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._switch_tab("Map")
        self._tick()

    def _switch_tab(self, key):
        self._tab = key
        for k, b in self._tab_btns.items():
            b.config(bg=ACCENT if k == key else CARD,
                     fg=BG    if k == key else WHITE)
        for w in self._content.winfo_children():
            w.destroy()
        {"Map":       self._tab_map,
         "Distances": self._tab_distances,
         "Vehicles":  self._tab_vehicles,
         "Bookings":  self._tab_bookings,
         "Admin":     self._tab_admin}.get(key, lambda: None)()

    def _logout(self):
        self._ctrl.logout()
        self._show_login()
    def _tab_map(self):
        pane = tk.Frame(self._content, bg=BG)
        pane.pack(fill="both", expand=True)

        left = tk.Frame(pane, bg=BG2, width=290)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        tk.Label(left, text="Filter", font=FH,
                 bg=BG2, fg=WHITE).pack(anchor="w", padx=12, pady=(12, 4))
        fbf = tk.Frame(left, bg=BG2)
        fbf.pack(fill="x", padx=8)
        self._fbtns = {}
        for vt in ["All", "Jeepney", "Multicab", "Bus"]:
            b = tk.Button(fbf, text=vt, font=FS,
                          bg=ACCENT if vt == "All" else CARD,
                          fg=BG    if vt == "All" else WHITE,
                          relief="flat", cursor="hand2",
                          command=lambda v=vt: self._set_filter(v))
            b.pack(side="left", padx=2, pady=4, ipady=4, ipadx=6)
            self._fbtns[vt] = b

        tk.Label(left, text="Vehicles", font=FH,
                 bg=BG2, fg=WHITE).pack(anchor="w", padx=12, pady=(10, 4))
        sf = tk.Frame(left, bg=BG2)
        sf.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb = tk.Scrollbar(sf)
        sb.pack(side="right", fill="y")
        self._vlist = tk.Listbox(sf, font=FC, bg=CARD, fg=WHITE,
                                 selectbackground=ACCENT,
                                 selectforeground=BG,
                                 relief="flat", activestyle="none",
                                 yscrollcommand=sb.set)
        self._vlist.pack(fill="both", expand=True)
        sb.config(command=self._vlist.yview)
        self._vlist.bind("<<ListboxSelect>>", self._on_vsel)

        right = tk.Frame(pane, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._map_cv = tk.Canvas(right, bg="#08111E", height=390,
                                 highlightthickness=1,
                                 highlightbackground=CARD)
        self._map_cv.pack(fill="x")
        self._map_cv.bind("<Configure>", lambda e: self._draw_map())

        self._detail = tk.Frame(right, bg=BG2)
        self._detail.pack(fill="both", expand=True, pady=(8, 0))
        tk.Label(self._detail,
                 text="Select a vehicle from the list to view details",
                 font=FN, bg=BG2, fg=DIM).pack(expand=True)

        self._refresh_vlist()
        self._draw_map()

    def _set_filter(self, vt):
        self._filter.set(vt)
        for k, b in self._fbtns.items():
            b.config(bg=ACCENT if k == vt else CARD,
                     fg=BG    if k == vt else WHITE)
        self._refresh_vlist()

    def _refresh_vlist(self):
        if not hasattr(self, "_vlist"): return
        sel = self._vlist.curselection()
        fleet = self._ctrl.get_fleet(self._filter.get())
        sel_id = fleet[sel[0]].id if sel and sel[0] < len(fleet) else None
        self._vlist.delete(0, tk.END)
        new_sel = None
        for i, v in enumerate(fleet):
            dot  = "🔴" if v.is_full else ("🟡" if v.occupancy_pct > .75 else "🟢")
            line = (f"{dot} {v.id} {v.vehicle_type:<8} "
                    f"{v.passengers:2d}/{v.capacity} ETA:{v.eta_minutes}m")
            self._vlist.insert(tk.END, line)
            if v.id == sel_id: new_sel = i
        if new_sel is not None:
            self._vlist.selection_set(new_sel)

    def _on_vsel(self, _=None):
        if not hasattr(self, "_vlist"): return
        sel   = self._vlist.curselection()
        fleet = self._ctrl.get_fleet(self._filter.get())
        if not sel or sel[0] >= len(fleet): return
        self._show_detail(fleet[sel[0]])

    def _show_detail(self, v: Vehicle):
        for w in self._detail.winfo_children(): w.destroy()
        self._sel_v = v

        hdr = tk.Frame(self._detail, bg=CARD2, padx=14, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"{v.get_icon()}  {v.id}  —  {v.vehicle_type}",
                 font=FH, bg=CARD2, fg=ACCENT).pack(side="left")
        sc = RED if v.is_full else (ORANGE if v.occupancy_pct > .75 else GREEN)
        tk.Label(hdr, text=f"● {v.status}", font=FH,
                 bg=CARD2, fg=sc).pack(side="right")

        body = tk.Frame(self._detail, bg=BG2, padx=10, pady=6)
        body.pack(fill="both", expand=True)

        info = v.get_info() 
        tile_data = [
            ("🛣️  From",       info["From"],        ACCENT),
            ("📍  To",          info["To"],          ACCENT),
            ("📏  Distance",    info["Route km"],    WHITE),
            ("⏱️  ETA",         info["ETA"],         GREEN),
            ("👥  Passengers",  info["Passengers"],  ORANGE),
            ("📝  Note",        info.get("Note",""), DIM),
        ]
        for i, (lbl, val, col) in enumerate(tile_data):
            t = tk.Frame(body, bg=CARD, padx=12, pady=8)
            t.grid(row=i//2, column=i%2, padx=4, pady=3, sticky="nsew")
            body.columnconfigure(i%2, weight=1)
            tk.Label(t, text=lbl, font=FS, bg=CARD, fg=DIM).pack(anchor="w")
            tk.Label(t, text=val, font=("Segoe UI", 11, "bold"),
                     bg=CARD, fg=col).pack(anchor="w")

        bf = tk.Frame(body, bg=BG2)
        bf.grid(row=3, column=0, columnspan=2, padx=4, pady=(4, 0), sticky="ew")
        tk.Label(bf, text="Occupancy", font=FS, bg=BG2, fg=DIM).pack(anchor="w")
        bar_bg = tk.Frame(bf, bg="#0A1628", height=14)
        bar_bg.pack(fill="x", pady=2)
        bc = RED if v.is_full else (ORANGE if v.occupancy_pct > .75 else GREEN)
        tk.Frame(bar_bg, bg=bc, height=14).place(
            relx=0, rely=0, relwidth=v.occupancy_pct, height=14)
        tk.Label(bf, text=f"{int(v.occupancy_pct*100)}%",
                 font=FS, bg=BG2, fg=bc).pack(anchor="e")

        if not self._ctrl.current_user.is_admin:
            tk.Button(body, text="🎫  Book This Vehicle", font=FN,
                      bg=GREEN if not v.is_full else CARD,
                      fg=BG   if not v.is_full else DIM,
                      relief="flat", cursor="hand2",
                      state="normal" if not v.is_full else "disabled",
                      command=lambda: self._book(v)
                      ).grid(row=4, column=0, columnspan=2,
                             padx=4, pady=(8, 0), sticky="ew", ipady=6)

    def _book(self, v: Vehicle):
        win = tk.Toplevel(self)
        win.title("Book Vehicle")
        win.geometry("360x260")
        win.configure(bg=BG2)
        win.grab_set()

        tk.Label(win, text=f"Book  {v.get_icon()} {v.id}",
                 font=FH, bg=BG2, fg=ACCENT).pack(pady=(18, 4))
        tk.Label(win, text=f"{v.origin.name}  →  {v.destination.name}",
                 font=FN, bg=BG2, fg=WHITE).pack()
        tk.Label(win, text="Select your pickup location:",
                 font=FS, bg=BG2, fg=DIM).pack(pady=(14, 4))

        pickup_var = tk.StringVar()
        names      = sorted(self._ctrl.locations.keys())
        cb = ttk.Combobox(win, textvariable=pickup_var,
                          values=names, state="readonly",
                          font=FN, width=30)
        cb.pack(ipady=4)
        cb.set(v.origin.name)

        err = tk.Label(win, text="", font=FS, bg=BG2, fg=RED)
        err.pack()

        def confirm():
            try:
                b = self._ctrl.book_vehicle(v.id, pickup_var.get())
                win.destroy()
                messagebox.showinfo("Booking Confirmed",
                                    f"✅  Booking {b.booking_id} confirmed!\n"
                                    f"Vehicle : {b.vehicle.id} ({b.vehicle.vehicle_type})\n"
                                    f"Pickup  : {b.pickup.name}\n"
                                    f"ETA     : ~{b.vehicle.eta_minutes} min")
            except (VehicleCapacityError, LocationNotFoundError,
                    AuthenticationError, ValueError) as e:
                err.config(text=str(e))

        tk.Button(win, text="Confirm Booking", font=FH,
                  bg=GREEN, fg=BG, relief="flat", cursor="hand2",
                  command=confirm).pack(pady=(10, 0), ipady=7, padx=30, fill="x")

    def _draw_map(self):
        if not hasattr(self, "_map_cv"): return
        cv = self._map_cv
        cv.delete("all")
        W = cv.winfo_width()  or 800
        H = cv.winfo_height() or 390

        for x in range(0, W, 55): cv.create_line(x,0,x,H, fill="#0C1E35", width=1)
        for y in range(0, H, 40): cv.create_line(0,y,W,y, fill="#0C1E35", width=1)

        locs = self._ctrl.locations

        for orig, dest, _ in AppController.ROUTE_DEFS:
            if orig in locs and dest in locs:
                x1,y1 = latlon_xy(locs[orig].lat, locs[orig].lon, W, H)
                x2,y2 = latlon_xy(locs[dest].lat, locs[dest].lon, W, H)
                cv.create_line(x1,y1,x2,y2, fill="#162C48", width=1, dash=(4,3))

        for name, loc in locs.items():
            x, y = latlon_xy(loc.lat, loc.lon, W, H)
            col  = LCOLOR[loc.loc_type]
            r    = 5 if loc.loc_type == "City" else 3
            cv.create_oval(x-r,y-r,x+r,y+r, fill=col, outline="white", width=1)
            if loc.loc_type in ("City","Landmark"):
                cv.create_text(x+8, y, text=name, font=("Segoe UI",7),
                               fill=col, anchor="w")

        for v in self._ctrl.get_fleet(self._filter.get()):
            x, y = latlon_xy(v.current_lat, v.current_lon, W, H)
            col  = RED if v.is_full else VCOLOR[v.vehicle_type]
            cv.create_oval(x-6,y-6,x+6,y+6, fill=col, outline="white", width=1)
            cv.create_text(x, y-13, text=v.id, font=("Courier New",6), fill=col)

        for i,(lbl,col) in enumerate([("Jeepney",GOLD),("Multicab",GREEN),
                                       ("Bus",ACCENT),("FULL",RED)]):
            cv.create_oval(8,H-52+i*12,16,H-44+i*12, fill=col, outline="")
            cv.create_text(20,H-48+i*12, text=lbl,
                           font=("Segoe UI",7), fill=col, anchor="w")

        cv.create_text(W-4,4, text="LIVE MAP  ·  Surigao del Norte",
                       font=("Segoe UI",8), fill=DIM, anchor="ne")

    def _tab_distances(self):
        outer = tk.Frame(self._content, bg=BG)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="📊  Distance Calculator",
                 font=FBG, bg=BG, fg=WHITE).pack(anchor="w", pady=(8,10))

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)

        fA = tk.Frame(nb, bg=BG2)
        nb.add(fA, text="  All → Surigao City  ")
        rows = [(n, lt, f"{km:.2f} km",
                 f"~{max(1,int(km/35*60))} min",
                 f"~{max(1,int(km/60*60))} min")
                for n, lt, km in self._ctrl.all_to_surigao()]
        self._dist_table(fA,
            "Distance from all locations to Surigao City",
            ("Location", "Type", "Distance", "ETA Jeepney", "ETA Bus"),
            rows)

        fB = tk.Frame(nb, bg=BG2)
        nb.add(fB, text="  → Pier 2  ")
        origins_B = ["Punta Bilar","Serna","Terminal (Brgy Luna)"]
        rows_B = [(o, f"{km:.2f} km",
                   f"~{max(1,int(km/35*60))} min",
                   f"~{max(1,int(km/40*60))} min")
                  for o,km in self._ctrl.distances_to("Pier 2 (Pantalan 2)", origins_B)]
        self._dist_table(fB,
            "Distance to Pier 2 (Pantalan 2)",
            ("From", "Distance", "ETA Jeepney", "ETA Multicab"),
            rows_B)

        fC = tk.Frame(nb, bg=BG2)
        nb.add(fC, text="  → Terminal  ")
        origins_C = ["Placer","Sison","Mainit","Claver","Tagana-an","Bad-as"]
        rows_C = [(o, f"{km:.2f} km",
                   f"~{max(1,int(km/35*60))} min",
                   f"~{max(1,int(km/40*60))} min")
                  for o,km in self._ctrl.distances_to("Terminal (Brgy Luna)", origins_C)]
        self._dist_table(fC,
            "Distance to Terminal (Brgy Luna)",
            ("From", "Distance", "ETA Jeepney", "ETA Multicab"),
            rows_C)

    def _dist_table(self, parent, title, cols, rows):
        tk.Label(parent, text=title, font=FH,
                 bg=BG2, fg=ACCENT).pack(anchor="w", padx=14, pady=(10,6))
        tv = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=160, anchor="center")
        for r in rows:
            tv.insert("", tk.END, values=r)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, padx=(14,0), pady=(0,14))
        sb.pack(side="left", fill="y", pady=(0,14))

    def _tab_vehicles(self):
        outer = tk.Frame(self._content, bg=BG)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="📋  Live Vehicle Fleet",
                 font=FBG, bg=BG, fg=WHITE).pack(anchor="w", pady=(8,10))

        cols = ("ID","Type","Icon","From","To",
                "Passengers","Capacity","Occupancy","ETA","Status")
        tv = ttk.Treeview(outer, columns=cols, show="headings")
        widths = [65,80,50,185,185,90,80,90,80,70]
        for c,w in zip(cols,widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")
        self._fleet_tv = tv
        self._populate_fleet_tv()

        sb = ttk.Scrollbar(outer, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, pady=(0,8))
        sb.pack(side="left", fill="y", pady=(0,8))

    def _populate_fleet_tv(self):
        if not hasattr(self,"_fleet_tv"): return
        tv = self._fleet_tv
        for r in tv.get_children(): tv.delete(r)
        for v in self._ctrl.get_fleet():
            tv.insert("", tk.END, values=(
                v.id, v.vehicle_type, v.get_icon(),
                v.origin.name, v.destination.name,
                v.passengers, v.capacity,
                f"{int(v.occupancy_pct*100)}%",
                f"{v.eta_minutes}m", v.status
            ))

    def _tab_bookings(self):
        outer = tk.Frame(self._content, bg=BG)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="🎫  My Bookings",
                 font=FBG, bg=BG, fg=WHITE).pack(anchor="w", pady=(8,10))

        cols = ("Booking ID","Vehicle","Pickup","Status","Date/Time")
        tv = ttk.Treeview(outer, columns=cols, show="headings", height=16)
        widths = [110,110,200,100,200]
        for c,w in zip(cols,widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        rows = self._ctrl.get_my_bookings()
        if rows:
            for r in rows:
                tv.insert("", tk.END, values=(
                    r["booking_id"], r["vehicle_id"],
                    r["pickup"], r["status"], r["created_at"]))
        else:
            tv.insert("", tk.END, values=(
                "—", "No bookings yet", "—", "—", "—"))

        sb = ttk.Scrollbar(outer, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, pady=(0,8))
        sb.pack(side="left", fill="y", pady=(0,8))

    def _tab_admin(self):
        outer = tk.Frame(self._content, bg=BG)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="🔧  Admin Panel — All Bookings",
                 font=FBG, bg=BG, fg=WHITE).pack(anchor="w", pady=(8,10))

        cols = ("Booking ID","Username","Vehicle","Pickup","Status","Date/Time")
        tv = ttk.Treeview(outer, columns=cols, show="headings", height=16)
        widths = [110,110,100,190,100,190]
        for c,w in zip(cols,widths):
            tv.heading(c, text=c)
            tv.column(c, width=w, anchor="center")

        for r in self._ctrl.get_all_bookings():
            tv.insert("", tk.END, values=(
                r["booking_id"], r["username"], r["vehicle_id"],
                r["pickup"], r["status"], r["created_at"]))

        sb = ttk.Scrollbar(outer, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="left", fill="both", expand=True, pady=(0,8))
        sb.pack(side="left", fill="y", pady=(0,8))

    def _tick(self):
        if not self._running: return
        self._ctrl.tick_fleet()
        if self._tab == "Map":
            self._draw_map()
            self._refresh_vlist()
            if hasattr(self,"_sel_v"):
                self._show_detail(self._sel_v)
        elif self._tab == "Vehicles":
            self._populate_fleet_tv()
        self.after(900, self._tick)

    def _on_close(self):
        self._running = False
        self._ctrl.close()
        self.destroy()

def main():
    try:
        controller = AppController()
        app        = AppView(controller)
        app.mainloop()
    except DatabaseError as e:
        import tkinter.messagebox as mb
        mb.showerror("Database Error", str(e))
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror("Unexpected Error", str(e))


if __name__ == "__main__":
    main()
