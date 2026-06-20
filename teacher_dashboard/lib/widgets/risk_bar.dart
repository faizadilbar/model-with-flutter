// lib/widgets/risk_bar.dart

import 'package:flutter/material.dart';

class RiskBar extends StatelessWidget {
  final double value;
  final double maxValue;

  const RiskBar({super.key, required this.value, this.maxValue = 100});

  Color get _color {
    if (value >= 70) return const Color(0xFFE24B4A);
    if (value >= 40) return const Color(0xFFEF9F27);
    return const Color(0xFF639922);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('${value.toStringAsFixed(1)} / 100',
                style: TextStyle(
                    fontWeight: FontWeight.bold, color: _color, fontSize: 13)),
            Text(_label, style: TextStyle(color: _color, fontSize: 12)),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: (value / maxValue).clamp(0, 1),
            minHeight: 8,
            backgroundColor: Colors.grey[200],
            valueColor: AlwaysStoppedAnimation<Color>(_color),
          ),
        ),
      ],
    );
  }

  String get _label {
    if (value >= 70) return 'HIGH RISK';
    if (value >= 40) return 'MEDIUM';
    return 'LOW RISK';
  }
}
