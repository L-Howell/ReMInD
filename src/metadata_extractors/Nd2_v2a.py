import os
from nd2 import ND2File
from datetime import datetime

try:
    from .field_mapping import metadata_to_form_fields
except ImportError:  # allow running as a standalone script
    from field_mapping import metadata_to_form_fields

def extract_nd2_metadata(file_path):
    """
    Extract metadata from ND2 file and return a dictionary suitable for ReMInD.
    
    Args:
        file_path (str): Path to the ND2 file
        
    Returns:
        dict: Metadata dictionary with keys compatible with ReMInD fields
    """
    try:
        with ND2File(file_path) as nd2:
            metadata = {}
            
            # Basic file information
            metadata["File Path"] = file_path
            metadata["File Name"] = os.path.basename(file_path)
            
            # File size
            try:
                if hasattr(nd2, 'path') and nd2.path:
                    file_size = nd2.path.stat().st_size / (1024*1024)
                    metadata["File Size MB"] = f"{file_size:.2f}"
            except:
                metadata["File Size MB"] = "N/A"
            
            # Image dimensions
            try:
                metadata["Shape"] = str(nd2.shape) if hasattr(nd2, 'shape') else "N/A"
                metadata["Data Type"] = str(nd2.dtype) if hasattr(nd2, 'dtype') else "N/A"
            except:
                metadata["Shape"] = "N/A"
                metadata["Data Type"] = "N/A"
            
            # Dimension sizes
            try:
                if hasattr(nd2, 'sizes') and nd2.sizes:
                    sizes = nd2.sizes
                    metadata["Time Points"] = str(sizes.get('T', 1))
                    metadata["Channels"] = str(sizes.get('C', 1))
                    metadata["Z Slices"] = str(sizes.get('Z', 1))
                    metadata["Height"] = str(sizes.get('Y', 'N/A'))
                    metadata["Width"] = str(sizes.get('X', 'N/A'))
                else:
                    metadata.update({
                        "Time Points": "1",
                        "Channels": "1", 
                        "Z Slices": "1",
                        "Height": "N/A",
                        "Width": "N/A",
                    })
            except:
                metadata.update({
                    "Time Points": "N/A",
                    "Channels": "N/A", 
                    "Z Slices": "N/A",
                    "Height": "N/A",
                    "Width": "N/A",
                })
            
            # Experiment information
            try:
                if hasattr(nd2, 'experiment') and nd2.experiment:
                    exp = nd2.experiment
                    if isinstance(exp, (list, tuple)) and len(exp) > 0:
                        exp = exp[0]
                    
                    if exp:
                        metadata["Experiment Name"] = getattr(exp, 'name', 'N/A')
                        metadata["Experiment Description"] = getattr(exp, 'description', 'N/A')
                        metadata["Acquisition Date"] = getattr(exp, 'date', 'N/A')
                        metadata["Acquisition Time"] = getattr(exp, 'time', 'N/A')
            except:
                metadata.update({
                    "Experiment Name": "N/A",
                    "Experiment Description": "N/A",
                    "Acquisition Date": "N/A",
                    "Acquisition Time": "N/A",
                })
            
            # System information
            try:
                if hasattr(nd2, 'custom_data') and nd2.custom_data:
                    custom = nd2.custom_data
                    if isinstance(custom, dict):
                        # Look for hardware settings
                        if 'HardwareSetting' in custom:
                            hw = custom['HardwareSetting']
                            if isinstance(hw, dict):
                                metadata["System Name"] = hw.get('sCamera', 'N/A')
                                metadata["Camera Model"] = hw.get('sCameraModel', 'N/A')
            except:
                pass
            
            # CORRECTED: Objective and microscope information from metadata.channels
            try:
                if hasattr(nd2, 'metadata') and nd2.metadata:
                    meta = nd2.metadata
                    # Access channels directly from metadata object
                    if hasattr(meta, 'channels') and meta.channels:
                        channels = meta.channels
                        if len(channels) > 0:
                            first_channel = channels[0]
                            # Access microscope from channel
                            if hasattr(first_channel, 'microscope') and first_channel.microscope:
                                mic = first_channel.microscope
                                metadata["Objective Model"] = getattr(mic, 'objectiveName', 'N/A')
                                metadata["Objective Magnification"] = str(getattr(mic, 'objectiveMagnification', 'N/A'))
                                metadata["Objective NA"] = str(getattr(mic, 'objectiveNumericalAperture', 'N/A'))
                                metadata["Objective Medium"] = str(getattr(mic, 'immersionRefractiveIndex', 'N/A'))
                            else:
                                metadata.update({
                                    "Objective Model": "N/A",
                                    "Objective Magnification": "N/A",
                                    "Objective NA": "N/A",
                                    "Objective Medium": "N/A",
                                })
                    else:
                        metadata.update({
                            "Objective Model": "N/A",
                            "Objective Magnification": "N/A",
                            "Objective NA": "N/A",
                            "Objective Medium": "N/A",
                        })
            except Exception as e:
                metadata.update({
                    "Objective Model": "N/A",
                    "Objective Magnification": "N/A",
                    "Objective NA": "N/A",
                    "Objective Medium": "N/A",
                })
            
            # CORRECTED: Channel information from metadata.channels
            try:
                channel_names = []
                channel_details = []
                if hasattr(nd2, 'metadata') and nd2.metadata:
                    meta = nd2.metadata
                    # Access channels directly from metadata object
                    if hasattr(meta, 'channels') and meta.channels:
                        channels = meta.channels
                        for i, ch in enumerate(channels):
                            # Access channel metadata
                            if hasattr(ch, 'channel') and ch.channel:
                                ch_meta = ch.channel
                                name = getattr(ch_meta, 'name', f'Channel {i+1}')
                                channel_names.append(name)
                                
                                details = f"{name}"
                                em = getattr(ch_meta, 'emissionLambdaNm', None)
                                ex = getattr(ch_meta, 'excitationLambdaNm', None)
                                if em:
                                    details += f" (Em: {em}nm)"
                                if ex:
                                    details += f" (Ex: {ex}nm)"
                                channel_details.append(details)
                            else:
                                # Fallback: try to get name directly from channel object
                                name = getattr(ch, 'name', f'Channel {i+1}')
                                channel_names.append(name)
                                channel_details.append(name)
                
                metadata["Channel Names"] = channel_names if channel_names else ["N/A"]
                metadata["Channel Details"] = "\n".join(channel_details) if channel_details else "N/A"
            except Exception as e:
                metadata["Channel Names"] = ["N/A"]
                metadata["Channel Details"] = "N/A"
            
            # Pixel size information
            try:
                if hasattr(nd2, 'voxel_size') and nd2.voxel_size:
                    voxel = nd2.voxel_size
                    metadata["Pixel Size X"] = f"{voxel.x:.6f}" if hasattr(voxel, 'x') and voxel.x else "N/A"
                    metadata["Pixel Size Y"] = f"{voxel.y:.6f}" if hasattr(voxel, 'y') and voxel.y else "N/A"
                    metadata["Pixel Size Z"] = f"{voxel.z:.6f}" if hasattr(voxel, 'z') and voxel.z else "N/A"
                    metadata["Pixel Size Unit"] = "µm"
                else:
                    metadata.update({
                        "Pixel Size X": "N/A",
                        "Pixel Size Y": "N/A", 
                        "Pixel Size Z": "N/A",
                        "Pixel Size Unit": "N/A",
                    })
            except:
                metadata.update({
                    "Pixel Size X": "N/A",
                    "Pixel Size Y": "N/A", 
                    "Pixel Size Z": "N/A",
                    "Pixel Size Unit": "N/A",
                })
            
            # Additional metadata from text_info
            try:
                if hasattr(nd2, 'text_info') and nd2.text_info:
                    text_info = nd2.text_info
                    if isinstance(text_info, dict):
                        # Common text info fields
                        metadata["Document User Name"] = text_info.get('sUser', 'N/A')
                        metadata["Document Creation Date"] = text_info.get('dTimeStart', 'N/A')
                        metadata["Software Version"] = text_info.get('sSoftwareVersion', 'N/A')
                        metadata["Microscope Type"] = text_info.get('sMicroscopeType', 'N/A')
                        # ADD THIS LINE for Modality
                        metadata["Modality"] = text_info.get('Modality', 'N/A')
            except:
                pass
            
            # Format combined date/time if available
            try:
                date_str = metadata.get("Acquisition Date", "")
                time_str = metadata.get("Acquisition Time", "")
                if date_str != "N/A" and time_str != "N/A" and date_str and time_str:
                    metadata["Document Creation Date"] = f"{date_str} {time_str}"
                elif hasattr(nd2, 'attributes') and nd2.attributes:
                    # Try to get creation time from attributes
                    attrs = nd2.attributes
                    if 'textinfo' in attrs:
                        text_attrs = attrs['textinfo']
                        if 'dTimeStart' in text_attrs:
                            metadata["Document Creation Date"] = str(text_attrs['dTimeStart'])
            except:
                pass
            
            return metadata
            
    except Exception as e:
        raise Exception(f"Failed to extract ND2 metadata: {str(e)}")

def map_nd2_to_remind_fields(nd2_metadata):
    """
    Work out which ReMInD form fields can be filled from ND2 metadata.

    Args:
        nd2_metadata (dict): output of extract_nd2_metadata.

    Returns:
        dict: form field label -> text to put in that field, in the same form
        as metadata_to_form_fields: a field is included only when the file
        has a value for it. Missing keys, "" and "N/A" count as no value.

        "Objective" is built as "<magnification>x/<NA> <model>" when both
        numbers are known, otherwise it is the model alone. "Immersion" is
        derived from the refractive index: below 1.1 is "Air", below 1.4 is
        "Water", above 1.5 is "Oil". An index between 1.4 and 1.5 could be
        glycerol or silicone, so the field is left out. A non-numeric value
        is passed through as text.
    """
    def known(key):
        value = str(nd2_metadata.get(key, "")).strip()
        return "" if value == "N/A" else value

    model, mag, na = known("Objective Model"), known("Objective Magnification"), known("Objective NA")
    objective = f"{mag}x/{na} {model}".strip() if mag and na else model

    medium = known("Objective Medium")
    try:
        ri = float(medium)
        medium = "Air" if ri < 1.1 else "Water" if ri < 1.4 else "Oil" if ri > 1.5 else ""
    except ValueError:
        pass

    return metadata_to_form_fields({
        "Document Creation Date": known("Document Creation Date"),
        "System Name":            known("System Name"),
        "Objective Model":        objective,
        "Objective Medium":       medium,
        "Acquisition Modes":      known("Modality"),
        "Channel Names":          nd2_metadata.get("Channel Names"),
        "Size Z":                 known("Z Slices"),
        "Size T":                 known("Time Points"),
    })

# Example usage function for testing
def test_nd2_extraction(file_path):
    """Test function to extract and display ND2 metadata"""
    try:
        metadata = extract_nd2_metadata(file_path)
        remind_fields = map_nd2_to_remind_fields(metadata)
        
        print("=== ND2 METADATA ===")
        for key, value in metadata.items():
            print(f"{key}: {value}")
            
        print("\n=== REMIND FIELDS ===")
        for key, value in remind_fields.items():
            print(f"{key}: {value}")
            
        return metadata, remind_fields
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

if __name__ == "__main__":
    # Test with a file path
    test_file = input("Enter ND2 file path: ")
    if test_file and os.path.exists(test_file):
        test_nd2_extraction(test_file)