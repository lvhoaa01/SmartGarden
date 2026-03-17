from db.database import get_db_connection
from services.ai_service import analyze_environment_and_image

def process_and_store_telemetry(batch_id, temperature, humidity, avg_soil, light_lux, co2_level, image_bytes):
    camera_status = "OK"
    
    ai_reasoning, action_target = analyze_environment_and_image(
        temperature, humidity, avg_soil, light_lux, image_bytes
    )
    
    if ai_reasoning == "AI Offline":
        camera_status = "AI_OFFLINE"

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO Telemetry_Master 
        (batch_id, temperature, humidity, avg_soil, light_lux, co2_level, camera_status, disease_detected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, temperature, humidity, avg_soil, light_lux, co2_level, camera_status, 0))
    
    action_msg = "GIU NGUYEN"
    if action_target == 1:
        action_msg = "BAT BOM"
        cursor.execute("INSERT INTO Action_Logs (batch_id, action_type, trigger_source, reason) VALUES (?, 'PUMP_ON', 'QWEN_VLM', ?)", (batch_id, ai_reasoning[:250]))
    elif action_target == 2:
        action_msg = "BAT QUAT"
        cursor.execute("INSERT INTO Action_Logs (batch_id, action_type, trigger_source, reason) VALUES (?, 'FAN_ON', 'QWEN_VLM', ?)", (batch_id, ai_reasoning[:250]))
    elif action_target == 3:
        action_msg = "BOM + QUAT"
        cursor.execute("INSERT INTO Action_Logs (batch_id, action_type, trigger_source, reason) VALUES (?, 'PUMP_FAN_ON', 'QWEN_VLM', ?)", (batch_id, ai_reasoning[:250]))
    elif action_target == 5:
        action_msg = "BAT DEN"
        cursor.execute("INSERT INTO Action_Logs (batch_id, action_type, trigger_source, reason) VALUES (?, 'LIGHT_ON', 'QWEN_VLM', ?)", (batch_id, ai_reasoning[:250]))

    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "ai_reasoning": ai_reasoning,
        "ai_action_code": action_target,
        "message": action_msg
    }

def fetch_latest_telemetry(limit: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT TOP ({limit}) 
            CONVERT(varchar, timestamp, 108) as time_str,
            temperature, humidity, avg_soil, light_lux, co2_level, disease_detected
        FROM Telemetry_Master 
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    data = [
        {
            "time": row.time_str,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "soil": row.avg_soil,
            "light": row.light_lux,
            "co2": row.co2_level,
            "disease": row.disease_detected
        }
        for row in rows
    ]
    conn.close()
    return data[::-1]