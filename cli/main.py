"""
CLI หลักสำหรับระบบ Dhamma Automation
รองรับคำสั่งต่างๆ สำหรับการรัน AI Agents
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


import typer
from rich import box
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agents.trend_scout import TrendScoutAgent, TrendScoutInput
from automation_core.config import config
from automation_core.logging import get_logger

# สร้าง Typer app
app = typer.Typer(
    name="dhamma-automation",
    help="🙏 ระบบอัตโนมัติสำหรับการผลิตคอนเทนต์ช่อง YouTube ธรรมะดีดี",
    add_completion=False,
    rich_markup_mode="rich"
)

# Console สำหรับแสดงผล
console = Console()
logger = get_logger(__name__)


@app.command()
def trend_scout(
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="📁 ไฟล์ JSON ข้อมูลนำเข้าสำหรับ TrendScoutAgent",
        exists=True,
        readable=True
    ),
    output_file: Path = typer.Option(
        "output/trend_scout_result.json",
        "--out",
        "-o",
        help="📄 ไฟล์ผลลัพธ์ (JSON)"
    ),
    show_table: bool = typer.Option(
        True,
        "--table/--no-table",
        help="แสดงตารางผลลัพธ์"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="แสดงข้อมูลละเอียด"
    )
):
    """
    🔍 รัน TrendScoutAgent เพื่อวิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์
    
    ตัวอย่างการใช้งาน:
    
    dhamma-automation trend-scout --input mock_input.json --out result.json
    """

    console.print("\n🙏 [bold blue]ระบบอัตโนมัติ ธรรมะดีดี[/bold blue]")
    console.print("📊 รัน TrendScoutAgent v1.0.0\n")

    try:
        # โหลดข้อมูลนำเข้า
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # โหลดไฟล์ input
            task1 = progress.add_task("📖 กำลังโหลดข้อมูล...", total=100)
            progress.update(task1, advance=30)

            try:
                with open(input_file, encoding='utf-8') as f:
                    input_data_dict = json.load(f)
                progress.update(task1, advance=30)

                # แปลงเป็น Pydantic model
                input_data = TrendScoutInput(**input_data_dict)
                progress.update(task1, advance=40)

                if verbose:
                    console.print(f"✅ โหลดข้อมูลสำเร็จ: {len(input_data.keywords)} คำสำคัญ")

            except json.JSONDecodeError as e:
                console.print(f"❌ [red]ข้อผิดพลาดในไฟล์ JSON: {e}[/red]")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"❌ [red]ไม่สามารถโหลดข้อมูลได้: {e}[/red]")
                raise typer.Exit(1)

            # สร้าง Agent และรัน
            task2 = progress.add_task("🤖 กำลังวิเคราะห์เทรนด์...", total=100)

            try:
                agent = TrendScoutAgent()
                progress.update(task2, advance=20)

                result = agent.run(input_data)
                progress.update(task2, advance=80)

                if verbose:
                    console.print(f"✅ วิเคราะห์สำเร็จ: {len(result.topics)} หัวข้อ")

            except Exception as e:
                console.print(f"❌ [red]เกิดข้อผิดพลาดในการวิเคราะห์: {e}[/red]")
                if verbose:
                    console.print_exception()
                raise typer.Exit(1)

            # บันทึกผลลัพธ์
            task3 = progress.add_task("💾 กำลังบันทึกผลลัพธ์...", total=100)
            progress.update(task3, advance=30)

            try:
                # สร้างโฟลเดอร์หากไม่มี
                output_file.parent.mkdir(parents=True, exist_ok=True)

                progress.update(task3, advance=30)

                # บันทึกเป็น JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        result.model_dump(),
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str  # สำหรับ datetime
                    )

                progress.update(task3, advance=40)

                console.print(f"✅ บันทึกผลลัพธ์แล้ว: [green]{output_file}[/green]")

            except Exception as e:
                console.print(f"❌ [red]ไม่สามารถบันทึกผลลัพธ์ได้: {e}[/red]")
                raise typer.Exit(1)

        # แสดงตารางผลลัพธ์
        if show_table and result.topics:
            console.print("\n📊 [bold]ผลลัพธ์หัวข้อคอนเทนต์[/bold]")
            _display_topics_table(result.topics)

        # แสดงสรุปผลลัพธ์
        console.print("\n📈 [bold]สรุปผลลัพธ์[/bold]")
        console.print(f"• จำนวนหัวข้อ: [cyan]{len(result.topics)}[/cyan]")
        console.print(f"• หัวข้อที่พิจารณา: [cyan]{result.meta.total_candidates_considered}[/cyan]")
        console.print(f"• คะแนนเฉลี่ย: [cyan]{_calculate_average_score(result.topics):.3f}[/cyan]")

        if result.topics:
            best_topic = result.topics[0]
            console.print(f"• หัวข้อแนะนำ: [green]{best_topic.title}[/green] (คะแนน: {best_topic.scores.composite:.3f})")

        console.print("\n🎉 [bold green]เสร็จสิ้น![/bold green] ผลลัพธ์พร้อมใช้งาน")

    except KeyboardInterrupt:
        console.print("\n⏹️  หยุดการทำงานโดยผู้ใช้")
        raise typer.Exit(0)
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดไม่คาดคิด: {e}")
        console.print(f"❌ [red]เกิดข้อผิดพลาดไม่คาดคิด: {e}[/red]")
        raise typer.Exit(1)


def _display_topics_table(topics):
    """แสดงตารางหัวข้อคอนเทนต์"""

    table = Table(
        title="🏆 หัวข้อคอนเทนต์ที่แนะนำ",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("อันดับ", style="cyan", width=6, justify="center")
    table.add_column("หัวข้อ", style="white", min_width=25)
    table.add_column("เสาหลัก", style="yellow", width=15)
    table.add_column("คะแนนรวม", style="green", width=10, justify="center")
    table.add_column("การดูคาดการณ์", style="blue", width=12, justify="right")
    table.add_column("เหตุผล", style="dim white", width=20)

    for topic in topics[:10]:  # แสดงแค่ 10 อันดับแรก
        table.add_row(
            str(topic.rank),
            topic.title,
            topic.pillar,
            f"{topic.scores.composite:.3f}",
            f"{topic.predicted_14d_views:,}",
            topic.reason
        )

    console.print(table)


def _calculate_average_score(topics) -> float:
    """คำนวณคะแนนเฉลี่ย"""
    if not topics:
        return 0.0

    total_score = sum(topic.scores.composite for topic in topics)
    return total_score / len(topics)


@app.command()
def version():
    """📋 แสดงเวอร์ชันของระบบ"""
    console.print(f"🙏 [bold blue]Dhamma Automation[/bold blue] v{config.app_name}")
    console.print("📊 TrendScoutAgent v1.0.0")
    console.print("⚙️  Python CLI with Typer & Rich")


@app.command()
def config_info():
    """⚙️ แสดงข้อมูลการตั้งค่าปัจจุบัน"""
    console.print("📊 [bold]การตั้งค่าระบบ[/bold]")
    console.print(f"• App Name: [cyan]{config.app_name}[/cyan]")
    console.print(f"• Log Level: [cyan]{config.log_level}[/cyan]")
    console.print(f"• Data Dir: [cyan]{config.data_dir}[/cyan]")
    console.print(f"• Log File: [cyan]{config.log_file}[/cyan]")


if __name__ == "__main__":
    app()
