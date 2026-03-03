import subprocess
import sys
import os
import re

def validar_tiempo(t):
    if t == "":
        return None
    patron = r"^\d{2}:\d{2}:\d{2}$"
    if re.match(patron, t):
        return t
    else:
        print("Formato inválido. Usa HH:MM:SS (ej: 00:05:30)")
        return None

def main():
    if len(sys.argv) < 2:
        print("Uso: python cortar_video.py video.mp4")
        sys.exit(1)

    input_video = sys.argv[1]

    if not os.path.exists(input_video):
        print("El archivo no existe.")
        sys.exit(1)

    print("\nIntroduce los tiempos en formato HH:MM:SS")
    print("Deja vacío si no quieres aplicar ese límite.\n")

    inicio = validar_tiempo(input("Desde (opcional): ").strip())
    fin = validar_tiempo(input("Hasta (opcional): ").strip())

    if inicio is None and fin is None:
        print("No se especificó ningún límite. Cancelando.")
        sys.exit(0)

    nombre_salida = os.path.splitext(input_video)[0] + "_corte.mp4"

    comando = ["ffmpeg"]

    if inicio:
        comando += ["-ss", inicio]

    comando += ["-i", input_video]

    if fin:
        comando += ["-to", fin]

    comando += ["-c", "copy", nombre_salida]

    print("\nEjecutando:")
    print(" ".join(comando))
    print()

    subprocess.run(comando)

    print("\nListo:", nombre_salida)

if __name__ == "__main__":
    main()
