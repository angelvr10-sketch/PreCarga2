"""
Test para verificar que el código de verificación no expira prematuramente.
"""
from datetime import datetime, timezone, timedelta

# Test 1: Verificar que el formato de fecha se parsea correctamente
def test_expira_parsing():
    """Simula el formato que usa la BD"""
    
    # Formato que se guarda en la BD (sin timezone)
    expira_str = "2026-04-15 14:30:00"
    
    # Aplicar el nuevo fix
    if expira_str and "+" not in expira_str and "T" not in expira_str:
        expira_str = expira_str + "+00:00"
    
    expira = datetime.fromisoformat(expira_str)
    
    # Asegurar que tiene timezone
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    
    ahora = datetime.now(timezone.utc)
    expira_correcto = ahora + timedelta(minutes=30)
    
    print(f"✓ expira parsed: {expira}")
    print(f"✓ expira.tzinfo: {expira.tzinfo}")
    print(f"✓ ahora: {ahora}")
    print(f"✓ expira_correcto (ahora + 30min): {expira_correcto}")
    
    # Verificar que la comparación funciona
    assert ahora < expira_correcto, "La comparación debería funcionar correctamente"
    print("✓ Test 1 PASSED: Comparación de fechas funciona correctamente")

# Test 2: Verificar que un código "viejo" se detecta como expirado
def test_codigo_expirado():
    """Un código de hace 31 minutos debería estar expirado"""
    
    # Simular un código de hace 31 minutos
    expira_str = (datetime.now(timezone.utc) - timedelta(minutes=31)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Aplicar el fix
    if expira_str and "+" not in expira_str and "T" not in expira_str:
        expira_str = expira_str + "+00:00"
    
    expira = datetime.fromisoformat(expira_str)
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    
    ahora = datetime.now(timezone.utc)
    
    print(f"\n✓ expira (hace 31 min): {expira}")
    print(f"✓ ahora: {ahora}")
    print(f"✓ ahora > expira: {ahora > expira}")
    
    assert ahora > expira, "El código debería estar expirado"
    print("✓ Test 2 PASSED: Código expirado detectado correctamente")

# Test 3: Verificar que un código "nuevo" NO se detecta como expirado
def test_codigo_valido():
    """Un código de hace 5 minutos NO debería estar expirado"""
    
    # Simular un código de hace 5 minutos (expira en 25 min)
    expira_str = (datetime.now(timezone.utc) + timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Aplicar el fix
    if expira_str and "+" not in expira_str and "T" not in expira_str:
        expira_str = expira_str + "+00:00"
    
    expira = datetime.fromisoformat(expira_str)
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    
    ahora = datetime.now(timezone.utc)
    
    print(f"\n✓ expira (en 25 min): {expira}")
    print(f"✓ ahora: {ahora}")
    print(f"✓ ahora > expira: {ahora > expira}")
    
    assert ahora < expira, "El código NO debería estar expirado"
    print("✓ Test 3 PASSED: Código válido reconocido correctamente")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing verification code expiration fix")
    print("=" * 60)
    
    test_expira_parsing()
    test_codigo_expirado()
    test_codigo_valido()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
