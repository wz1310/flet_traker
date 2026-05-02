import flet as ft
import threading
from datetime import datetime
from tracker_service import TrackerService
from config import AppConfig


def main(page: ft.Page):
    page.title = "HP Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.GREY_900
    page.padding = 0
    page.window.width = 400
    page.window.height = 750

    config = AppConfig()
    tracker = TrackerService(config)

    # ── State ──────────────────────────────────────────────
    is_tracking = False
    location_history = []
    current_tab = 0

    # ── Status card refs ───────────────────────────────────
    status_icon = ft.Icon(ft.Icons.LOCATION_OFF, color=ft.Colors.RED_400, size=40)
    status_text = ft.Text(
        "Tracking Tidak Aktif",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.RED_400,
    )
    status_subtitle = ft.Text(
        "Tekan tombol untuk mulai tracking",
        size=12,
        color=ft.Colors.GREY_400,
    )
    lat_text = ft.Text("--", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    lon_text = ft.Text("--", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    acc_text = ft.Text("Akurasi: --", size=12, color=ft.Colors.GREY_400)
    last_update_text = ft.Text("Belum ada update", size=11, color=ft.Colors.GREY_500)

    # ── Settings fields ────────────────────────────────────
    interval_field = ft.TextField(
        value=str(config.interval_seconds),
        label="Interval (detik)",
        width=140,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        focused_border_color=ft.Colors.BLUE_200,
        color=ft.Colors.WHITE,
    )
    telegram_token_field = ft.TextField(
        value=config.telegram_token,
        label="Telegram Bot Token",
        password=True,
        can_reveal_password=True,
        focused_border_color=ft.Colors.BLUE_200,
        color=ft.Colors.WHITE,
        expand=True,
    )
    telegram_chat_id_field = ft.TextField(
        value=config.telegram_chat_id,
        label="Telegram Chat ID",
        focused_border_color=ft.Colors.BLUE_200,
        color=ft.Colors.WHITE,
        expand=True,
    )
    device_name_field = ft.TextField(
        value=config.device_name,
        label="Nama Perangkat",
        focused_border_color=ft.Colors.BLUE_200,
        color=ft.Colors.WHITE,
        expand=True,
    )

    # ── History list (Column inside scroll, not ListView) ──
    history_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    # ── Log ────────────────────────────────────────────────
    log_text = ft.Text("", size=11, color=ft.Colors.GREY_400, selectable=True)

    # ── Buttons ────────────────────────────────────────────
    toggle_btn = ft.FilledButton(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PLAY_ARROW, size=18),
                ft.Text("MULAI TRACKING", size=13, weight=ft.FontWeight.BOLD),
            ],
            tight=True,
            spacing=6,
        ),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_700,
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        width=210,
        height=50,
        on_click=lambda e: toggle_tracking(e),
    )

    send_now_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.SEND, size=16), ft.Text("Kirim Sekarang", size=12)],
            tight=True,
            spacing=6,
        ),
        disabled=True,
        style=ft.ButtonStyle(
            color=ft.Colors.BLUE_300,
            side=ft.BorderSide(color=ft.Colors.BLUE_400, width=1),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=lambda e: send_now(e),
    )

    # ── Tab indicator (manual, since TabBar has no selected_index) ──
    tab_labels = ["Riwayat", "Pengaturan", "Log"]
    tab_icons = [ft.Icons.HISTORY, ft.Icons.SETTINGS, ft.Icons.TERMINAL]

    def make_tab_btn(index: int):
        is_active = index == current_tab
        return ft.TextButton(
            content=ft.Column(
                [
                    ft.Icon(
                        tab_icons[index],
                        size=20,
                        color=ft.Colors.BLUE_400 if is_active else ft.Colors.GREY_500,
                    ),
                    ft.Text(
                        tab_labels[index],
                        size=11,
                        color=ft.Colors.BLUE_400 if is_active else ft.Colors.GREY_500,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            on_click=lambda e, i=index: switch_tab(i),
            expand=True,
        )

    tab_row = ft.Row(spacing=0, expand=True)

    def rebuild_tab_row():
        tab_row.controls = [make_tab_btn(i) for i in range(3)]

    rebuild_tab_row()

    # ── Tab content views ──────────────────────────────────
    history_view = ft.Container(
        content=ft.Column(
            [history_column],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        expand=True,
        padding=ft.Padding.only(top=8),
        visible=True,
    )

    settings_view = ft.Container(
        content=ft.Column(
            [
                ft.Text("Konfigurasi Tracking", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([interval_field]),
                ft.Divider(color=ft.Colors.GREY_700),
                ft.Text("Perangkat", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row([device_name_field]),
                ft.Divider(color=ft.Colors.GREY_700),
                ft.Text("Telegram Notifikasi", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text(
                    "Buat bot via @BotFather, isi token & chat ID di bawah",
                    size=11,
                    color=ft.Colors.GREY_400,
                ),
                ft.Row([telegram_token_field]),
                ft.Row([telegram_chat_id_field]),
                ft.FilledButton(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.SAVE, size=16), ft.Text("Simpan Pengaturan", size=13)],
                        tight=True,
                        spacing=6,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_700,
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                    on_click=lambda e: save_settings(),
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
        expand=True,
        visible=False,
    )

    log_view = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Log Aktivitas", size=13, color=ft.Colors.GREY_300),
                        ft.Container(expand=True),
                        ft.TextButton(
                            content=ft.Text("Hapus", color=ft.Colors.RED_300, size=12),
                            on_click=lambda e: clear_log(),
                        ),
                    ]
                ),
                ft.Container(
                    content=ft.Column(
                        [log_text],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    bgcolor=ft.Colors.BLACK,
                    border_radius=8,
                    padding=10,
                    expand=True,
                ),
            ],
            spacing=8,
            expand=True,
        ),
        padding=12,
        expand=True,
        visible=False,
    )

    # ── Helpers ────────────────────────────────────────────
    def switch_tab(index: int):
        nonlocal current_tab
        current_tab = index
        history_view.visible = index == 0
        settings_view.visible = index == 1
        log_view.visible = index == 2
        rebuild_tab_row()
        page.update()

    def clear_log():
        log_text.value = ""
        page.update()

    def add_log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        current = log_text.value or ""
        lines = current.split("\n") if current else []
        lines.insert(0, f"[{ts}] {msg}")
        log_text.value = "\n".join(lines[:50])
        page.update()

    def refresh_history():
        history_column.controls.clear()
        for h in location_history[:30]:
            maps_url = f"https://maps.google.com/?q={h['lat']},{h['lon']}"
            history_column.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.LOCATION_PIN, color=ft.Colors.RED_400, size=16),
                            ft.Column(
                                [
                                    ft.Text(h["time"], size=11, color=ft.Colors.GREY_400),
                                    ft.Text(
                                        f"{h['lat']:.5f}, {h['lon']:.5f}",
                                        size=12,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.MAP,
                                icon_color=ft.Colors.BLUE_300,
                                icon_size=18,
                                tooltip="Buka di Maps",
                                url=maps_url,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=ft.Colors.GREY_800,
                    border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    margin=ft.Margin.symmetric(horizontal=8),
                )
            )

    def update_location_ui(loc: dict):
        lat_text.value = f"{loc['lat']:.6f}"
        lon_text.value = f"{loc['lon']:.6f}"
        acc_text.value = f"Akurasi: ±{loc.get('accuracy', '?')} m"
        last_update_text.value = f"Update: {datetime.now().strftime('%H:%M:%S')}"

        entry = {
            "time": datetime.now().strftime("%d/%m %H:%M:%S"),
            "lat": loc["lat"],
            "lon": loc["lon"],
        }
        location_history.insert(0, entry)
        if len(location_history) > 100:
            location_history.pop()

        refresh_history()
        page.update()

    def on_location_received(loc: dict, sent_ok: bool):
        update_location_ui(loc)
        status = "✓ Terkirim ke Telegram" if sent_ok else "⚠ Gagal kirim"
        add_log(f"Lokasi: {loc['lat']:.5f}, {loc['lon']:.5f} — {status}")

    # ── Toggle tracking ────────────────────────────────────
    def toggle_tracking(e):
        nonlocal is_tracking
        is_tracking = not is_tracking

        if is_tracking:
            try:
                config.interval_seconds = int(interval_field.value)
            except ValueError:
                config.interval_seconds = 30
            config.telegram_token = telegram_token_field.value.strip()
            config.telegram_chat_id = telegram_chat_id_field.value.strip()
            config.device_name = device_name_field.value.strip() or "HP Saya"
            config.save()

            tracker.start(callback=on_location_received)

            toggle_btn.content = ft.Row(
                [ft.Icon(ft.Icons.STOP, size=18), ft.Text("STOP TRACKING", size=13, weight=ft.FontWeight.BOLD)],
                tight=True, spacing=6,
            )
            toggle_btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.RED_700,
                shape=ft.RoundedRectangleBorder(radius=12),
            )
            status_icon.name = ft.Icons.LOCATION_ON
            status_icon.color = ft.Colors.GREEN_400
            status_text.value = "Tracking Aktif"
            status_text.color = ft.Colors.GREEN_400
            status_subtitle.value = (
                f"Interval: {config.interval_seconds}s · "
                f"Telegram: {'✓' if config.telegram_token else '✗'}"
            )
            send_now_btn.disabled = False
            add_log("Tracking dimulai")
        else:
            tracker.stop()
            toggle_btn.content = ft.Row(
                [ft.Icon(ft.Icons.PLAY_ARROW, size=18), ft.Text("MULAI TRACKING", size=13, weight=ft.FontWeight.BOLD)],
                tight=True, spacing=6,
            )
            toggle_btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_700,
                shape=ft.RoundedRectangleBorder(radius=12),
            )
            status_icon.name = ft.Icons.LOCATION_OFF
            status_icon.color = ft.Colors.RED_400
            status_text.value = "Tracking Tidak Aktif"
            status_text.color = ft.Colors.RED_400
            status_subtitle.value = "Tekan tombol untuk mulai tracking"
            send_now_btn.disabled = True
            add_log("Tracking dihentikan")

        page.update()

    def send_now(e):
        def _send():
            loc = tracker.get_location_once()
            if loc:
                sent = tracker.send_to_telegram(loc)
                on_location_received(loc, sent)
            else:
                add_log("⚠ Gagal mendapatkan lokasi")
        threading.Thread(target=_send, daemon=True).start()

    def save_settings():
        try:
            config.interval_seconds = int(interval_field.value)
        except ValueError:
            pass
        config.telegram_token = telegram_token_field.value.strip()
        config.telegram_chat_id = telegram_chat_id_field.value.strip()
        config.device_name = device_name_field.value.strip() or "HP Saya"
        config.save()
        add_log("Pengaturan disimpan")
        page.open(
            ft.SnackBar(
                content=ft.Text("Pengaturan disimpan!"),
                bgcolor=ft.Colors.GREEN_700,
            )
        )

    # ── Layout ─────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.SHIELD, color=ft.Colors.BLUE_300, size=26),
                ft.Text("HP Tracker", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(expand=True),
                ft.Text("v1.0", size=11, color=ft.Colors.GREY_500),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.GREY_800,
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border.only(bottom=ft.BorderSide(color=ft.Colors.GREY_700, width=1)),
    )

    status_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [status_icon, ft.Column([status_text, status_subtitle], spacing=2)],
                    spacing=12,
                ),
                ft.Divider(color=ft.Colors.GREY_700),
                ft.Row(
                    [
                        ft.Column(
                            [ft.Text("LATITUDE", size=10, color=ft.Colors.GREY_500), lat_text],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True,
                        ),
                        ft.VerticalDivider(color=ft.Colors.GREY_700, width=1),
                        ft.Column(
                            [ft.Text("LONGITUDE", size=10, color=ft.Colors.GREY_500), lon_text],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True,
                        ),
                    ],
                    height=60,
                ),
                ft.Row([acc_text, ft.Container(expand=True), last_update_text]),
            ],
            spacing=10,
        ),
        bgcolor=ft.Colors.GREY_800,
        border_radius=14,
        padding=16,
        margin=ft.Margin.symmetric(horizontal=12, vertical=8),
        border=ft.Border.all(color=ft.Colors.GREY_700, width=1),
    )

    tab_bar_container = ft.Container(
        content=tab_row,
        bgcolor=ft.Colors.GREY_800,
        border=ft.Border.only(bottom=ft.BorderSide(color=ft.Colors.GREY_700, width=1)),
        padding=ft.Padding.symmetric(vertical=4),
    )

    page.add(
        ft.Column(
            [
                header,
                status_card,
                ft.Container(
                    content=ft.Row(
                        [toggle_btn, send_now_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    padding=ft.Padding.symmetric(vertical=6),
                ),
                tab_bar_container,
                ft.Container(
                    content=ft.Stack([history_view, settings_view, log_view]),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    add_log("Aplikasi siap. Konfigurasi Telegram lalu mulai tracking.")

ft.run(main)
