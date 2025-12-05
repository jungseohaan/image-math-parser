"""
직각삼각형 ABC를 기반으로 두 개의 원이 그려진 기하학적 도형
- 점 B가 직각, AB=3, BC=4
- 점 A를 중심으로 하는 작은 원 (반지름 AD)
- 점 C, E, G를 지나는 큰 원
- 점 H는 큰 원 위의 점
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Arc, FancyArrowPatch
import numpy as np
import platform
import os
import tempfile
from PIL import Image

# 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

def draw_triangle_with_circles():
    fig, ax = plt.subplots(figsize=(10, 10))

    # 수능 스타일 색상
    LINE_COLOR = 'black'
    POINT_COLOR = 'black'

    # 좌표 설정 (B를 원점으로)
    B = np.array([0, 0])
    A = np.array([0, 3])  # AB = 3
    C = np.array([4, 0])  # BC = 4

    # D: AB를 2:1로 내분하는 점 (A에서 B 방향으로 2/3 지점)
    # AD : DB = 2 : 1 이므로 D = A + (2/3)(B - A)
    D = A + (2/3) * (B - A)  # D = (0, 1)
    AD = np.linalg.norm(D - A)  # AD = 2

    # E: A를 중심, 반지름 AD인 원과 AC의 교점
    # AC 방향 단위벡터
    AC = C - A
    AC_unit = AC / np.linalg.norm(AC)
    E = A + AD * AC_unit

    # F: A를 중심, 반지름 AD인 원과 직선 AB의 교점 (D가 아닌 점)
    # AB 직선 위에서 A로부터 거리 AD인 점 (D의 반대편)
    F = A + AD * np.array([0, 1])  # A 위쪽 방향

    # G: 호 EF 위의 점 (CG = 2√6이 되도록)
    # A를 중심으로 하는 원 위의 점 중에서 CG = 2√6인 점을 찾음
    CG_target = 2 * np.sqrt(6)

    # 원 위의 점 G 찾기 (각도 탐색)
    # A 중심, 반지름 AD인 원의 매개변수
    theta_E = np.arctan2(E[1] - A[1], E[0] - A[0])
    theta_F = np.arctan2(F[1] - A[1], F[0] - A[0])

    # E와 F 사이의 호에서 G 찾기
    for theta in np.linspace(theta_E, theta_F + 2*np.pi if theta_F < theta_E else theta_F, 100):
        G_candidate = A + AD * np.array([np.cos(theta), np.sin(theta)])
        if abs(np.linalg.norm(G_candidate - C) - CG_target) < 0.1:
            G = G_candidate
            break
    else:
        # 찾지 못하면 호의 중간점
        theta_mid = (theta_E + theta_F) / 2
        G = A + AD * np.array([np.cos(theta_mid), np.sin(theta_mid)])

    # 세 점 C, E, G를 지나는 원 구하기 (외접원)
    def circumcircle(p1, p2, p3):
        """세 점을 지나는 원의 중심과 반지름"""
        ax = p1[0]; ay = p1[1]
        bx = p2[0]; by = p2[1]
        cx = p3[0]; cy = p3[1]

        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-10:
            return None, None

        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d

        center = np.array([ux, uy])
        radius = np.linalg.norm(p1 - center)
        return center, radius

    big_center, big_radius = circumcircle(C, E, G)

    # H: 큰 원 위의 점 (∠HCG = ∠BAC를 만족)
    # ∠BAC 계산
    BA = A - B
    CA = A - C
    angle_BAC = np.arccos(np.dot(-CA, BA - A + A) / (np.linalg.norm(CA) * np.linalg.norm(BA)))
    # 간단하게: A에서 B, C를 바라보는 각도
    vec_AB = B - A
    vec_AC = C - A
    angle_BAC = np.arccos(np.dot(vec_AB, vec_AC) / (np.linalg.norm(vec_AB) * np.linalg.norm(vec_AC)))

    # H는 큰 원 위에서 적절한 위치에 배치
    # C에서 G를 바라보는 방향에서 angle_BAC만큼 회전한 방향
    vec_CG = G - C
    angle_CG = np.arctan2(vec_CG[1], vec_CG[0])
    angle_H = angle_CG + angle_BAC

    # H는 큰 원 위의 점
    if big_center is not None:
        H = big_center + big_radius * np.array([np.cos(angle_H + 0.3), np.sin(angle_H + 0.3)])
    else:
        H = G + np.array([1, 1])

    # ===== 그리기 시작 =====

    # 1. 직각삼각형 ABC
    triangle = plt.Polygon([A, B, C], fill=False, edgecolor=LINE_COLOR, linewidth=1.5)
    ax.add_patch(triangle)

    # 직각 표시 (B에서)
    rect_size = 0.3
    rect = plt.Rectangle(B, rect_size, rect_size, fill=False, edgecolor=LINE_COLOR, linewidth=1)
    ax.add_patch(rect)

    # 2. 작은 원 (A 중심, 반지름 AD)
    small_circle = Circle(A, AD, fill=False, edgecolor=LINE_COLOR, linewidth=1.5)
    ax.add_patch(small_circle)

    # 3. 큰 원 (C, E, G를 지나는 원)
    if big_center is not None and big_radius is not None:
        big_circle = Circle(big_center, big_radius, fill=False, edgecolor=LINE_COLOR, linewidth=1.5, linestyle='--')
        ax.add_patch(big_circle)

    # 4. 점들 표시
    points = {
        'A': A, 'B': B, 'C': C, 'D': D, 'E': E, 'F': F, 'G': G, 'H': H
    }

    # 라벨 오프셋 설정
    label_offsets = {
        'A': (-0.3, 0.2),
        'B': (-0.3, -0.3),
        'C': (0.2, -0.3),
        'D': (-0.4, 0),
        'E': (0.2, 0.1),
        'F': (-0.3, 0.2),
        'G': (0.2, 0.1),
        'H': (0.2, 0.1)
    }

    for name, point in points.items():
        ax.plot(point[0], point[1], 'ko', markersize=5)
        offset = label_offsets.get(name, (0.2, 0.2))
        ax.annotate(name, point, textcoords="offset points",
                   xytext=(offset[0]*30, offset[1]*30), fontsize=12, fontweight='bold')

    # 5. 추가 선분들
    # AD 선분 (이미 AB의 일부)

    # AE 선분
    ax.plot([A[0], E[0]], [A[1], E[1]], color=LINE_COLOR, linewidth=1, linestyle=':')

    # AG 선분
    ax.plot([A[0], G[0]], [A[1], G[1]], color=LINE_COLOR, linewidth=1, linestyle=':')

    # CG 선분
    ax.plot([C[0], G[0]], [C[1], G[1]], color=LINE_COLOR, linewidth=1)

    # GH 선분
    ax.plot([G[0], H[0]], [G[1], H[1]], color=LINE_COLOR, linewidth=1.5)

    # CH 선분
    ax.plot([C[0], H[0]], [C[1], H[1]], color=LINE_COLOR, linewidth=1, linestyle=':')

    # CE 선분
    ax.plot([C[0], E[0]], [C[1], E[1]], color=LINE_COLOR, linewidth=1, linestyle=':')

    # 6. 축 설정
    ax.set_xlim(-2, 7)
    ax.set_ylim(-2, 6)
    ax.set_aspect('equal')
    ax.axis('off')

    # 제목
    ax.set_title('직각삼각형 ABC와 두 원', fontsize=14, pad=20)

    # 범례 정보 (텍스트로)
    info_text = (
        f"AB = 3, BC = 4, ∠B = π/2\n"
        f"D: AB를 2:1로 내분\n"
        f"작은 원: 중심 A, 반지름 AD\n"
        f"큰 원: C, E, G를 지남"
    )
    ax.text(5, 4.5, info_text, fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # 저장 (90도 회전)
    output_path = '/Users/seohan/works/pdf-parser/geometry_output.png'

    # 임시 파일로 먼저 저장
    fd, temp_path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    plt.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    # PIL로 90도 회전
    img = Image.open(temp_path)
    img_rotated = img.rotate(-90, expand=True)  # 시계 방향 90도
    img_rotated.save(output_path)

    # 임시 파일 삭제
    os.remove(temp_path)

    print(f"그래프가 저장되었습니다: {output_path}")
    return output_path


if __name__ == '__main__':
    draw_triangle_with_circles()
