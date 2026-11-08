# CLI (командная строка)

import sys
import os
from typing import List, Optional
from .lexer import Lexer, LexerError
from .parser import Parser, ParseError
from .analyzer import Analyzer, AnalysisError
from .interpreter import Interpreter
from .messages import error_msg, warning_msg


def main():
    """Точка входа CLI."""
    # Настраиваем UTF-8 для stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(2)
    
    command = sys.argv[1]
    
    if command == '--версия':
        print_version()
        sys.exit(0)
    
    elif command == 'запусти':
        if len(sys.argv) < 3:
            print_usage()
            sys.exit(2)
        
        file_path = sys.argv[2]
        virtual_time = '--без_пауз' in sys.argv
        network = '--сеть' in sys.argv
        
        run_file(file_path, virtual_time, network)
    
    elif command == 'проверь':
        if len(sys.argv) < 3:
            print_usage()
            sys.exit(2)
        
        file_path = sys.argv[2]
        check_file(file_path)
    
    elif command == 'собери':
        if len(sys.argv) < 3:
            print_usage()
            sys.exit(2)
        
        file_path = sys.argv[2]
        build_file(file_path)
    
    elif command == 'бутыль':
        if len(sys.argv) < 3:
            print_usage()
            sys.exit(2)
        
        subcommand = sys.argv[2]
        if subcommand == 'открой':
            if len(sys.argv) < 4:
                print_usage()
                sys.exit(2)
            package = sys.argv[3]
            bottle_open(package)
        elif subcommand == 'допей':
            if len(sys.argv) < 4:
                print_usage()
                sys.exit(2)
            package = sys.argv[3]
            bottle_close(package)
        else:
            print_usage()
            sys.exit(2)
    
    else:
        print_usage()
        sys.exit(2)


def print_usage():
    print("""Использование: гоп <команда> [аргументы]

Команды:
  гоп запусти файл.слыш [--без_пауз] [--сеть]  Запустить программу
  гоп проверь файл.слыш                        Проверить синтаксис
  гоп собери файл.слыш                         Собрать бочку (заглушка)
  гоп --версия                                 Показать версию
  бутыль открой <пакет>                        Установить пакет (заглушка)
  бутыль допей <пакет>                         Удалить пакет (заглушка)""", file=sys.stderr)


def print_version():
    print("ГопЛя 2.2 «Ля'Мадмуазель». Бонжур, епт! Дворник на посту.")


def read_source(file_path: str) -> str:
    """Читает исходный файл с поддержкой UTF-8 и BOM."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Удаляем BOM если есть
        if data.startswith(b'\xef\xbb\xbf'):
            data = data[3:]
        
        # Декодируем как UTF-8
        return data.decode('utf-8')
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден: {file_path}", file=sys.stderr)
        sys.exit(2)
    except UnicodeDecodeError:
        print(f"Ошибка: Файл не в кодировке UTF-8: {file_path}", file=sys.stderr)
        sys.exit(2)


def run_file(file_path: str, virtual_time: bool, network: bool):
    """Запускает файл .слыш."""
    source = read_source(file_path)
    
    try:
        # Лексинг
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        # Парсинг
        parser = Parser(tokens)
        program = parser.parse()
        
        # Анализ
        analyzer = Analyzer(program, strict_mode=program.header.strict)
        errors, warnings = analyzer.analyze()
        
        for msg, line in errors:
            print(msg, file=sys.stderr)
        for msg, line in warnings:
            print(msg, file=sys.stderr)
        
        if errors:
            sys.exit(2)
        
        # Интерпретация
        interpreter = Interpreter(program, virtual_time, network)
        exit_code = interpreter.run()
        sys.exit(exit_code)
        
    except LexerError as e:
        print(error_msg("E001", e.line), file=sys.stderr)
        sys.exit(2)
    except ParseError as e:
        print(e.message, file=sys.stderr)
        sys.exit(2)
    except AnalysisError as e:
        print(e.message, file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\nПрервано пользователем", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Внутренняя ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def check_file(file_path: str):
    """Проверяет синтаксис файла без запуска."""
    source = read_source(file_path)
    
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        program = parser.parse()
        
        analyzer = Analyzer(program, strict_mode=program.header.strict)
        errors, warnings = analyzer.analyze()
        
        for msg, line in errors:
            print(msg, file=sys.stderr)
        for msg, line in warnings:
            print(msg, file=sys.stderr)
        
        if errors:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except LexerError as e:
        print(error_msg("E001", e.line), file=sys.stderr)
        sys.exit(2)
    except ParseError as e:
        print(e.message, file=sys.stderr)
        sys.exit(2)
    except AnalysisError as e:
        print(e.message, file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Внутренняя ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def build_file(file_path: str):
    """Собирает исполняемый файл (заглушка)."""
    print("Бутыль пока пустая, мон ами.", file=sys.stderr)
    sys.exit(2)


def bottle_open(package: str):
    """Устанавливает пакет (заглушка)."""
    print("Бутыль пока пустая, мон ами.", file=sys.stderr)
    sys.exit(2)


def bottle_close(package: str):
    """Удаляет пакет (заглушка)."""
    print("Бутыль пока пустая, мон ами.", file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
    main()