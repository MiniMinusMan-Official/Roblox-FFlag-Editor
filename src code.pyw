import dearpygui.dearpygui as dpg
import os
import subprocess
import json
import requests
import threading
import time
import stat
import tkinter as tk
from tkinter import filedialog as tkFileDialog

FLAGS_URL = "https://raw.githubusercontent.com/MaximumADHD/Roblox-Client-Tracker/refs/heads/roblox/FVariables.txt"

custom_json_path = ""
use_custom_path = False
use_application_settings_wrapper = False

IXP_SETTINGS_PATH = os.path.join(os.getenv("LOCALAPPDATA", ""), "Roblox", "ClientSettings", "IxpSettings.json")

def fetch_flags():
    try:
        response = requests.get(FLAGS_URL, verify=False, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        allowed_prefixes = ("DFInt", "DFFlag", "DFString")
        flags = []
        for line in lines:
            if line.startswith(("[C++]", "[Lua]")) and " " in line:
                flag_name = line.split(" ", 1)[1].strip()
                if flag_name.startswith(allowed_prefixes):
                    flags.append(flag_name)
        print(f"Fetched {len(flags)} DFFlags")
        return flags
    except requests.exceptions.RequestException as e:
        print(f"Error fetching DFFlags: {e}")
        dpg.set_value("log", dpg.get_value("log") + f"\nError fetching DFFlags: {e}. Check internet connection.")
        return []

def fetch_flags_F():
    try:
        response = requests.get(FLAGS_URL, verify=False, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
        allowed_prefixes_F = ("FInt", "FFlag", "FString")
        flags_F = []
        for line in lines:
            if line.startswith(("[C++]", "[Lua]")) and " " in line:
                flag_name_F = line.split(" ", 1)[1].strip()
                if flag_name_F.startswith(allowed_prefixes_F):
                    flags_F.append(flag_name_F)
        print(f"Fetched {len(flags_F)} FFlags")
        return flags_F
    except requests.exceptions.RequestException as e:
        print(f"Error fetching FFlags: {e}")
        dpg.set_value("log", dpg.get_value("log") + f"\nError fetching FFlags: {e}. Check internet connection.")
        return []

visible_fflags = [str(f) for f in fetch_flags()]
all_fastflags = visible_fflags

visible_fflags_F = [str(x) for x in fetch_flags_F()]
all_fastflags_F = visible_fflags_F

def button_callback(sender, app_data, user_data):
    print(f"Clicked flag: {user_data}")
    dpg.set_value("custom_fflag", user_data)

def update_fflag_table():
    if dpg.does_item_exist("button_container"):
        dpg.delete_item("button_container", children_only=True)
        if not visible_fflags:
            dpg.add_text("No matching flags.", parent="button_container")
            return
        for flag in visible_fflags:
            dpg.add_button(label=str(flag), callback=button_callback, user_data=flag, parent="button_container")
    else:
        print("Warning: button_container does not exist yet.")

def search_fflags_callback(sender, app_data):
    global visible_fflags
    search = app_data.lower()
    visible_fflags = [flag for flag in all_fastflags if search in flag.lower()]
    update_fflag_table()

def update_fflag_table_F():
    if dpg.does_item_exist("button_container_F"):
        dpg.delete_item("button_container_F", children_only=True)
        if not visible_fflags_F:
            dpg.add_text("No matching flags.", parent="button_container_F")
            return
        for flag_F in visible_fflags_F:
            dpg.add_button(label=str(flag_F), callback=button_callback, user_data=flag_F, parent="button_container_F")
    else:
        print("Warning: button_container_F does not exist yet.")

def search_fflags_callback_F(sender, app_data):
    global visible_fflags_F
    search = app_data.lower()
    visible_fflags_F = [flag_F for flag_F in all_fastflags_F if search in flag_F.lower()]
    update_fflag_table_F()


def get_roblox_folder():
    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return None
    versions_path = os.path.join(local_app_data, "Roblox", "Versions")
    if not os.path.exists(versions_path):
        return None
    for root, dirs, files in os.walk(versions_path):
        if "RobloxPlayerBeta.exe" in files:
            return root
    return None

def get_client_app_settings_path():
    global custom_json_path, use_custom_path
    if use_custom_path and os.path.isfile(custom_json_path):
        return custom_json_path
    else:
        folder = get_roblox_folder()
        if folder:
            return os.path.join(folder, "ClientSettings", "ClientAppSettings.json")
        return None

def create_client_settings_dir():
    global custom_json_path, use_custom_path
    if use_custom_path:
        settings_folder = os.path.dirname(custom_json_path)
    else:
        folder = get_roblox_folder()
        if folder is None:
            dpg.set_value("log", dpg.get_value("log") + "\nRoblox installation not found.")
            return None
        settings_folder = os.path.join(folder, "ClientSettings")
    
    if not settings_folder:
        settings_folder = "."
    
    if not os.path.exists(settings_folder):
        try:
            os.makedirs(settings_folder)
            dpg.set_value("log", dpg.get_value("log") + f"\nCreated ClientSettings directory at: {settings_folder}")
        except OSError as e:
            dpg.set_value("log", dpg.get_value("log") + f"\nError creating ClientSettings directory: {e}")
            return None
    return settings_folder

def set_read_only(file_path, read_only):
    """Sets or removes the read-only file attribute."""
    if not os.path.exists(file_path):
        return

    try:
        current_stat = os.stat(file_path).st_mode
        if read_only:
            os.chmod(file_path, current_stat & ~stat.S_IWRITE)
        else:
            os.chmod(file_path, current_stat | stat.S_IWRITE)
        return True
    except Exception as e:
        dpg.set_value("log", dpg.get_value("log") + f"\nError setting Read-Only for {os.path.basename(file_path)}: {e}")
        return False

def get_read_only_state(file_path):
    if not os.path.exists(file_path):
        return False
    try:
        # Check if S_IWRITE bit is NOT set, meaning it's read-only
        return not (os.stat(file_path).st_mode & stat.S_IWRITE)
    except Exception:
        return False

def load_json_file(json_path):
    """General function to load a JSON file, temporarily removing read-only."""
    if not json_path:
        return {}

    # Ensure folder exists
    json_dir = os.path.dirname(json_path)
    os.makedirs(json_dir, exist_ok=True)
    
    set_read_only(json_path, False)

    if not os.path.exists(json_path):
        try:
            with open(json_path, "w") as f:
                json.dump({}, f, indent=4)
            dpg.set_value("log", dpg.get_value("log") + f"\nJSON file not found at: {os.path.basename(json_path)}. Created new file with empty data.")
        except Exception as e:
            dpg.set_value("log", dpg.get_value("log") + f"\nFailed to create JSON file at: {json_path}: {e}")
            return {}

    try:
        with open(json_path, "r") as f:
            loaded_data = json.load(f)
            if json_path.endswith("ClientAppSettings.json") and use_application_settings_wrapper and "applicationSettings" in loaded_data and isinstance(loaded_data["applicationSettings"], dict):
                return loaded_data["applicationSettings"]
            else:
                return loaded_data
    except json.JSONDecodeError as e:
        dpg.set_value("log", dpg.get_value("log") + f"\nError decoding JSON from {os.path.basename(json_path)}: {e}. Starting with empty data.")
        return {}
    except Exception as e:
        dpg.set_value("log", dpg.get_value("log") + f"\nError loading JSON from {os.path.basename(json_path)}: {e}")
        return {}


def load_all_settings():
    """Loads and merges flags from ClientAppSettings.json and IxpSettings.json."""
    client_path = get_client_app_settings_path()
    ixp_path = IXP_SETTINGS_PATH

    client_data = load_json_file(client_path)
    ixp_data = load_json_file(ixp_path)
    
    merged_data = {}
    merged_data.update(ixp_data)
    merged_data.update(client_data)
    
    return merged_data

def save_all_settings(data):
    """Saves the given data to BOTH ClientAppSettings.json and IxpSettings.json.
    Sets IxpSettings.json to Read-Only, but leaves ClientAppSettings.json writeable."""
    
    client_path = get_client_app_settings_path()
    ixp_path = IXP_SETTINGS_PATH
    
    if not client_path or not ixp_path:
        dpg.set_value("log", dpg.get_value("log") + "\nCould not determine file paths. Save aborted.")
        return

    if not create_client_settings_dir():
        return

    try:
        client_data_to_save = data
        if use_application_settings_wrapper:
            client_data_to_save = {"applicationSettings": data}
            
        with open(client_path, "w") as f:
            json.dump(client_data_to_save, f, indent=4)
        dpg.set_value("log", dpg.get_value("log") + f"\nSaved to ClientAppSettings.json (Writeable).")
        set_read_only(client_path, False)
    except Exception as e:
        dpg.set_value("log", dpg.get_value("log") + f"\nError saving ClientAppSettings.json: {e}")

    try:
        set_read_only(ixp_path, False)
        with open(ixp_path, "w") as f:
            json.dump(data, f, indent=4)
        dpg.set_value("log", dpg.get_value("log") + f"\nSaved to IxpSettings.json (Read-Only).")
        set_read_only(ixp_path, True)
    except Exception as e:
        dpg.set_value("log", dpg.get_value("log") + f"\nError saving IxpSettings.json: {e}")
    
    dpg.set_value("log", dpg.get_value("log") + "\nFiles saved. Restart Roblox to see changes.")

def toggle_humanoid_outline():
    data = load_all_settings()
    flag = "DFFlagDebugDrawBroadPhaseAABBs"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled HumanoidOutline")
    else:
        data[flag] = "True"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled HumanoidOutline")
    save_all_settings(data)

def toggle_diddler_proxy():
    data = load_all_settings()
    proxy_flags = ["DFStringDebugPlayerHttpProxyUrl", "DFStringHttpCurlProxyHostAndPort", "DFFlagDebugEnableHttpProxy", "DFStringHttpCurlProxyHostAndPortForExternalUrl", "DFIntSecondsBetweenDynamicVariableReloading"]

    if all(flag in data for flag in proxy_flags):
        for flag in proxy_flags:
            data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled the funny proxy")
    else:
        data["DFStringDebugPlayerHttpProxyUrl"] = "127.0.0.1:8888"
        data["DFStringHttpCurlProxyHostAndPort"] = "127.0.0.1:8888"
        data["DFFlagDebugEnableHttpProxy"] = "True"
        data["DFStringHttpCurlProxyHostAndPortForExternalUrl"] = "127.0.0.1:8888"
        data["DFIntSecondsBetweenDynamicVariableReloading"] = "1"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled the funny proxy")
    save_all_settings(data)

def toggle_invisible():
    data = load_all_settings()
    proxy_flags = ["DFIntPhysicsSenderMaxBandwidthBps", "DFIntPhysicsSenderMaxBandwidthBpsScaling"]

    if all(flag in data for flag in proxy_flags):
        for flag in proxy_flags:
            data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled invisibility [test]")
    else:
        data["DFIntPhysicsSenderMaxBandwidthBps"] = "-1"
        data["DFIntPhysicsSenderMaxBandwidthBpsScaling"] = "0"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled invisibility [test]")
    save_all_settings(data)

def toggle_disable_remotes():
    data = load_all_settings()
    flag = "DFIntRemoteEventSingleInvocationSizeLimit"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nRemotes are back! (off)")
    else:
        data[flag] = "1"
        dpg.set_value("log", dpg.get_value("log") + "\nNo more remotes! (on)")
    save_all_settings(data)

def toggle_auto_unmute():
    data = load_all_settings()
    flag = "FFlagDebugDefaultChannelStartMuted"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Unmute on Join")
    else:
        data[flag] = "False"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Unmute on Join")
    save_all_settings(data)

def toggle_hyperthreading():
    data = load_all_settings()
    flag = "FFlagRenderCheckThreading"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Hyperthreading")
    else:
        data[flag] = "True"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Hyperthreading")
    save_all_settings(data)

def toggle_hide_layered_clothing():
    data = load_all_settings()
    lc_flags = ["FStringAXCategories", "DFIntMaxCageDistance", "DFIntLCCageDeformLimit", "DFFlagCheckMaxCageDistance"]
    if all(flag in data for flag in lc_flags):
        for flag in lc_flags:
            data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Layered Clothing")
    else:
        data["FStringAXCategories"] = "True"
        data["DFIntMaxCageDistance"] = "-1"
        data["DFIntLCCageDeformLimit"] = "-1"
        data["DFFlagCheckMaxCageDistance"] = "True"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Layered Clothing")
    save_all_settings(data)

def toggle_hide_ingame_purchases():
    data = load_all_settings()
    flag = "DFFlagOrder66"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled In-game Purchases")
    else:
        data[flag] = "True"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled In-game Purchases")
    save_all_settings(data)

def toggle_noclip_camera():
    data = load_all_settings()
    flag = "DFIntRaycastMaxDistance"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Noclip Camera")
    else:
        data[flag] = "3"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Noclip Camera")
    save_all_settings(data)

def toggle_mesh_noclip():
    data = load_all_settings()
    flag = "DFIntPhysicsDecompForceUpgradeVersion"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Mesh Noclip")
    else:
        data[flag] = "1500"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Mesh Noclip")
    save_all_settings(data)

def toggle_terrainmesh_slide():
    data = load_all_settings()
    flag = "DFIntSmoothTerrainPhysicsRayAabbSlop"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Terrain/Mesh Slide")
    else:
        data[flag] = "-9999"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Terrain/Mesh Slide")
    save_all_settings(data)

def toggle_wallglide():
    data = load_all_settings()
    flag = "DFIntMaximumUnstickForceInGs"
    if flag in data:
        data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Wallglide")
    else:
        data[flag] = "-10"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Wallglide")
    save_all_settings(data)

def toggle_skeleton_esp():
    data = load_all_settings()
    skeleton_flags = ["DFFlagDebugDrawEnable", "DFFlagAnimatorDrawSkeletonAll", "DFIntAnimatorDrawSkeletonScalePercent"]
    if all(flag in data for flag in skeleton_flags):
        for flag in skeleton_flags:
            data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Skeleton ESP")
    else:
        data["DFFlagDebugDrawEnable"] = "True"
        data["DFFlagAnimatorDrawSkeletonAll"] = "True"
        data["DFIntAnimatorDrawSkeletonScalePercent"] = "250"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Skeleton ESP")
    save_all_settings(data)

def toggle_semi_fullbright():
    data = load_all_settings()
    fullbright_flags = ["FFlagFastGPULightCulling3", "FIntRenderShadowIntensity", "DFIntCullFactorPixelThresholdShadowMapHighQuality", "DFIntCullFactorPixelThresholdShadowMapLowQuality", "FFlagNewLightAttenuation", "FIntRenderShadowmapBias", "DFFlagDebugPauseVoxelizer"]
    if all(flag in data for flag in fullbright_flags):
        for flag in fullbright_flags:
            data.pop(flag)
        dpg.set_value("log", dpg.get_value("log") + "\nDisabled Semi-Fullbright")
    else:
        data["FFlagFastGPULightCulling3"] = "True"
        data["FIntRenderShadowIntensity"] = "0"
        data["DFIntCullFactorPixelThresholdShadowMapHighQuality"] = "2147483647"
        data["DFIntCullFactorPixelThresholdShadowMapLowQuality"] = "2147483647"
        data["FFlagNewLightAttenuation"] = "True"
        data["FIntRenderShadowmapBias"] = "-1"
        data["DFFlagDebugPauseVoxelizer"] = "True"
        dpg.set_value("log", dpg.get_value("log") + "\nEnabled Semi-Fullbright")
    save_all_settings(data)

def toggle_special_fflag(fflag, fval):
    if not fflag:
        dpg.set_value("log", dpg.get_value("log") + "\nError: FFlag name cannot be empty.")
        return

    data = load_all_settings()
    if fflag in data:
        data.pop(fflag)
        dpg.set_value("log", dpg.get_value("log") + f"\nRemoved flag: {fflag}")
    else:
        data[fflag] = f"{fval}"
        dpg.set_value("log", dpg.get_value("log") + f"\nAdded flag: {fflag} with value {fval}")
    save_all_settings(data)

def clear_all_json():
    save_all_settings({})
    dpg.set_value("log", dpg.get_value("log") + "\nCleared flags from both ClientAppSettings.json and IxpSettings.json.")

def set_wallglide_strength():
    data = load_all_settings()
    flag = "DFIntMaximumUnstickForceInGs"
    val = dpg.get_value("wallglide_strength")
    
    if val == 0:
        if flag in data:
            data.pop(flag)
            dpg.set_value("log", dpg.get_value("log") + f"\nCleared Wallglide flag.")
    else:
        if val > 0:
            val = -val
        data[flag] = str(val)
        dpg.set_value("log", dpg.get_value("log") + f"\nSet Wallglide Strength to {val}.")
        
    save_all_settings(data)

def open_native_file_dialog():
    global custom_json_path
    root = tk.Tk()
    root.withdraw()
    initial_dir = ""
    if os.path.exists(os.path.join(os.path.expanduser('~'), 'Downloads')):
        initial_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    elif get_roblox_folder():
        initial_dir = os.path.join(get_roblox_folder(), "ClientSettings")
    else:
        initial_dir = os.path.expanduser('~')

    file_path = tkFileDialog.askopenfilename(
        title="Select ClientAppSettings.json",
        initialdir=initial_dir,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )

    if file_path:
        custom_json_path = file_path
        dpg.set_value("custom_json_path_input", custom_json_path)
        dpg.set_value("log", dpg.get_value("log") + f"\nCustom JSON path set to: {custom_json_path}")
        dpg.set_value("use_custom_json_checkbox", True)
        global use_custom_path
        use_custom_path = True
        dpg.configure_item("custom_json_path_input", enabled=True)
        dpg.configure_item("browse_json_button", enabled=True)
    else:
        dpg.set_value("log", dpg.get_value("log") + "\nFile selection cancelled.")

    root.destroy()

def toggle_custom_path_checkbox(sender, app_data):
    global use_custom_path
    use_custom_path = app_data
    dpg.configure_item("custom_json_path_input", enabled=use_custom_path)
    dpg.configure_item("browse_json_button", enabled=use_custom_path)
    update_paths_display()
    update_json_fflags_display()

def toggle_application_settings_wrapper_checkbox(sender, app_data):
    global use_application_settings_wrapper
    use_application_settings_wrapper = app_data
    dpg.set_value("log", dpg.get_value("log") + f"\n'applicationSettings' wrapper set to: {use_application_settings_wrapper}. Will only apply to ClientAppSettings.")
    update_json_fflags_display()

def update_paths_display():
    client_path = get_client_app_settings_path() if get_client_app_settings_path() else "ClientAppSettings.json not found."
    ixp_path = IXP_SETTINGS_PATH if os.path.exists(os.path.dirname(IXP_SETTINGS_PATH)) else "IxpSettings.json path not found."
    
    dpg.set_value("selectable_text", f"{client_path}")
    dpg.set_value("selectable_text_b", f"{client_path}")
    dpg.set_value("i_selectable_text", f"{ixp_path}")
    
    client_ro = get_read_only_state(client_path) if client_path and os.path.exists(client_path) else "N/A"
    ixp_ro = get_read_only_state(IXP_SETTINGS_PATH) if os.path.exists(IXP_SETTINGS_PATH) else "N/A"
    
    dpg.set_value("client_ro_status", f"ClientAppSettings.json Read-Only: {client_ro} (Writeable)")
    dpg.set_value("ixp_ro_status", f"IxpSettings.json Read-Only: {ixp_ro} (Read-Only enforced)")

    if use_custom_path:
        dpg.set_value("custom_json_path_input", custom_json_path)
    else:
        dpg.set_value("custom_json_path_input", "")


dpg.create_context()
dpg.create_viewport(title="fluxusdude663's FFlag Editor", width=616, height=700)
dpg.set_viewport_resizable(False)

with dpg.window(label="RBLX FFlag Editor", width=600, height=661, no_title_bar=True, no_move=True, no_resize=True):
    with dpg.tab_bar():
        with dpg.tab(label="Basic Controls"):
            with dpg.child_window(height=500, width=-1, autosize_x=True):
                dpg.add_button(label="Close Editor", height=40, width=-1, callback=lambda: dpg.stop_dearpygui())
                dpg.add_button(label="Clear ALL Flags (Both Files)", width=-1, callback=clear_all_json)
                dpg.add_text("Toggle flags\n* DFFlag only\n| Mostly DFFlags, but contains 1 or 2 FFlags")
                dpg.add_button(label="* Toggle Remotes - on by default", width=-1, callback=toggle_disable_remotes)
                dpg.add_button(label="Toggle Unmute on Join", width=-1, callback=toggle_auto_unmute)
                dpg.add_button(label="Toggle Hyperthreading", width=-1, callback=toggle_hyperthreading)
                dpg.add_button(label="| Toggle Layered Clothing", width=-1, callback=toggle_hide_layered_clothing)
                dpg.add_button(label="* Toggle invisibility", width=-1, callback=toggle_invisible)
                dpg.add_button(label="* Toggle In-game Purchases", width=-1, callback=toggle_hide_ingame_purchases)
                dpg.add_button(label="* Toggle HumanoidOutline", width=-1, callback=toggle_humanoid_outline)
                dpg.add_button(label="* Toggle Wallglide", width=-1, callback=toggle_wallglide)
                dpg.add_button(label="Toggle Semi-Fullbright", width=-1, callback=toggle_semi_fullbright)
                dpg.add_button(label="* Toggle a proxy (is used to use DFFlags without restart)", width=-1, callback=toggle_diddler_proxy)
                dpg.add_button(label="* Toggle Noclip Camera", width=-1, callback=toggle_noclip_camera)
                dpg.add_button(label="* Toggle Mesh Noclip", width=-1, callback=toggle_mesh_noclip)
                dpg.add_button(label="* Toggle Terrain/Mesh Slide", width=-1, callback=toggle_terrainmesh_slide)
                dpg.add_button(label="* Toggle Skeleton ESP [Unstable, patched for new versions]", width=-1, callback=toggle_skeleton_esp)

                dpg.add_text("* Set Wallglide Strength (negative only, positive will be turned into negative):")
                dpg.add_input_int(tag="wallglide_strength", default_value=0, min_value=-5000, max_value=0)
                dpg.add_button(label="Set Strength", callback=set_wallglide_strength)

                dpg.add_text(f"These fastflags will be applied to both ClientAppSettings.json and IxpSettings.json.", wrap=500)
                dpg.add_text(f"ClientAppSettings.json", wrap=500)
                dpg.add_input_text(tag="selectable_text", default_value="", width=500, readonly=True)
                dpg.add_text(f"IxpSettings.json", wrap=500)
                dpg.add_input_text(tag="i_selectable_text", default_value="", width=500, readonly=True)

        with dpg.tab(label="Advanced Controls"):
            child_id = dpg.add_child_window(height=400, width=-1, autosize_x=False, autosize_y=False)
            dpg.push_container_stack(child_id)

            dpg.add_input_text(
                hint=f"Search for DFFlags ({len(all_fastflags)} flags fetched)",
                width=400,
                callback=search_fflags_callback,
            )

            with dpg.child_window(tag="button_container", height=167, width=-1, autosize_x=True):
                pass

            dpg.add_input_text(
                hint=f"Search for FFlags ({len(all_fastflags_F)} flags fetched)",
                width=400,
                callback=search_fflags_callback_F,
            )

            with dpg.child_window(tag="button_container_F", height=167, width=-1, autosize_x=True):
                pass

            with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingFixedFit, tag="fflag_table"):
                dpg.add_table_column()
                dpg.add_table_column()
            with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingFixedFit, tag="fflag_table_F"):
                dpg.add_table_column()
                dpg.add_table_column()

            update_fflag_table()
            update_fflag_table_F()

            dpg.pop_container_stack()

            with dpg.child_window(height=100, width=-1, autosize_x=True):
                dpg.add_input_text(label="", hint = "FFlag Name", width=425, tag="custom_fflag")
                dpg.add_same_line()
                dpg.add_input_text(label="", hint = "Value (true/0)", width=100, tag="custom_value")

                def add_special_fflag_ui():
                    fflag = dpg.get_value("custom_fflag")
                    fval = dpg.get_value("custom_value")
                    toggle_special_fflag(fflag, fval)
                dpg.add_button(label="Add Custom FFlag", callback=add_special_fflag_ui)

        with dpg.tab(label="Info / Other"):
            dpg.add_text("Roblox FFlag Editor\nby MiniMinusMan/computer dj\n@fluxusdude663", wrap=500)
            dpg.add_text("Coded In DPG 2.0.0 (Python)\nUsing MaximumADHD's FFlag Tracker\n", wrap=500)

            dpg.add_separator()
            dpg.add_text("Configuration File Settings:", color=[255, 255, 0])
            dpg.add_checkbox(label="Use Custom ClientAppSettings.json Path", tag="use_custom_json_checkbox", callback=toggle_custom_path_checkbox, default_value=False)
            dpg.add_checkbox(label="Wrap ClientAppSettings.json with 'applicationSettings' (for Fiddler Proxy)", tag="use_application_settings_wrapper_checkbox", callback=toggle_application_settings_wrapper_checkbox, default_value=False)

            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="custom_json_path_input", label="", hint="Custom ClientAppSettings.json Path", width=450, enabled=False)
                dpg.add_button(label="Browse", tag="browse_json_button", callback=open_native_file_dialog, enabled=False)

            dpg.add_text("Current ClientAppSettings.json file being used:", wrap=500)
            dpg.add_input_text(tag="selectable_text_b", default_value="", width=-1, readonly=True)
            dpg.add_text(tag="client_ro_status", default_value="ClientAppSettings.json Read-Only: N/A")
            dpg.add_text(tag="ixp_ro_status", default_value="IxpSettings.json Read-Only: N/A")

            dpg.add_separator()
            dpg.add_text("FFlag: Fast Flag\n*DFFlag: Dynamic Fast Flag\n\n* can be used with Fiddler (a proxy) to toggle DFFlags without restarting.")
            dpg.add_separator()
            dpg.add_text("All Active Flags (Mirrored in both JSON files):")
            dpg.add_input_text(tag="json_fflags_display", multiline=True, readonly=True, height=200, width=-1)

    dpg.add_input_text(tag="log", multiline=True, readonly=True, height=100, width=-1, default_value="FFlag Editor Initialized.")

dpg.setup_dearpygui()
dpg.show_viewport()

def update_json_fflags_display():
    """Fetches fflags + updates display"""
    data = load_all_settings()
    sorted_data = dict(sorted(data.items()))
    
    formatted = "\n".join(f"{k}: {v}" for k, v in sorted_data.items()) or f"No flags found in either JSON file.\nBoth files will be synchronized upon next save/toggle."
    
    if dpg.does_item_exist("json_fflags_display"):
        dpg.set_value("json_fflags_display", formatted)
        update_paths_display()
    else:
        # debug
        print("Warning: json_fflags_display item does not exist yet.")

def start_fflag_display_loop():
    """repeated updating"""
    def loop():
        while dpg.is_dearpygui_running():
            if dpg.is_dearpygui_running():
                update_json_fflags_display()
            time.sleep(1)
    
    # Check if a thread is already running to prevent duplicates
    if not any(t.name == "FFlagDisplayThread" for t in threading.enumerate()):
        threading.Thread(target=loop, daemon=True, name="FFlagDisplayThread").start()

update_paths_display()
start_fflag_display_loop()

dpg.start_dearpygui()
dpg.destroy_context()
