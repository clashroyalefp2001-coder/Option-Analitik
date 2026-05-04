# Strategy Robustness Audit Report
Generated at: 2026-05-02 23:18:20

## Executive Summary
- **Sharpe Elasticity**: 103.90% (STRESS)
- **Sign Flip Rate**: 2.56% (Healthy)
- **Average Stress Win Rate**: 58.95%

## Stress Matrix Results
| Test | Param | Value | Sharpe | CAGR | MaxDD | WinRate | PeakMargin |
| :--- | :---- | :---- | :----- | :--- | :---- | :------ | :--------- |
| seed_stability | seed | 0.0000 | 5.33 | 357.18% | 8.50% | 91.67% | 99.94% |
| seed_stability | seed | 1.0000 | 3.42 | 218.42% | 7.68% | 81.82% | 99.38% |
| seed_stability | seed | 2.0000 | 2.96 | 199.42% | 11.62% | 71.43% | 99.41% |
| seed_stability | seed | 3.0000 | 6.48 | 311.42% | 2.42% | 60.00% | 99.04% |
| seed_stability | seed | 4.0000 | 3.03 | 163.13% | 12.04% | 63.64% | 98.36% |
| seed_stability | seed | 5.0000 | 0.67 | 20.10% | 17.50% | 30.77% | 99.90% |
| seed_stability | seed | 6.0000 | 0.07 | -6.51% | 21.36% | 45.45% | 98.19% |
| seed_stability | seed | 7.0000 | 6.03 | 525.02% | 4.38% | 86.67% | 98.75% |
| seed_stability | seed | 8.0000 | 6.94 | 450.66% | 3.36% | 73.33% | 99.36% |
| seed_stability | seed | 9.0000 | 3.85 | 262.13% | 12.73% | 75.00% | 98.17% |
| stress | comm_per_contract | 0.6500 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | comm_per_contract | 1.0000 | 6.67 | 381.12% | 5.90% | 52.63% | 99.83% |
| stress | comm_per_contract | 1.5000 | 6.66 | 380.51% | 5.90% | 52.63% | 99.85% |
| stress | comm_per_contract | 2.0000 | 6.66 | 379.90% | 5.90% | 52.63% | 99.87% |
| stress | jump_lambda | 0.0000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | jump_lambda | 0.0500 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | jump_lambda | 0.1000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | jump_lambda | 0.2000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | jump_lambda | 0.4000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | market_basis_std | 0.0000 | 6.65 | 381.54% | 5.95% | 52.63% | 99.84% |
| stress | market_basis_std | 0.0100 | 6.66 | 381.54% | 5.92% | 52.63% | 99.82% |
| stress | market_basis_std | 0.0200 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | market_basis_std | 0.0400 | 6.70 | 381.56% | 5.84% | 58.82% | 99.79% |
| stress | market_basis_std | 0.0600 | 6.72 | 381.58% | 5.78% | 58.82% | 99.77% |
| stress | realized_vol | 0.1400 | 7.00 | 321.81% | 4.05% | 55.56% | 99.00% |
| stress | realized_vol | 0.1700 | 6.57 | 311.24% | 5.70% | 58.82% | 99.40% |
| stress | realized_vol | 0.2000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | realized_vol | 0.2300 | 6.50 | 364.58% | 6.99% | 68.75% | 99.95% |
| stress | realized_vol | 0.2600 | 6.20 | 423.56% | 8.13% | 73.33% | 99.70% |
| stress | sigma_for_pricing | 0.1600 | 6.33 | 364.29% | 6.28% | 68.75% | 99.84% |
| stress | sigma_for_pricing | 0.1800 | 6.28 | 371.69% | 6.67% | 55.56% | 99.44% |
| stress | sigma_for_pricing | 0.2000 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | sigma_for_pricing | 0.2200 | 6.87 | 377.03% | 5.66% | 55.56% | 99.28% |
| stress | sigma_for_pricing | 0.2400 | 6.76 | 346.85% | 5.78% | 62.50% | 99.66% |
| stress | slippage_pct | 0.0005 | 6.68 | 382.32% | 5.89% | 52.63% | 99.81% |
| stress | slippage_pct | 0.0010 | 6.67 | 381.55% | 5.90% | 52.63% | 99.81% |
| stress | slippage_pct | 0.0020 | 6.67 | 380.01% | 5.90% | 52.63% | 99.81% |
| stress | slippage_pct | 0.0030 | 6.66 | 378.48% | 5.91% | 52.63% | 99.81% |
| stress | slippage_pct | 0.0050 | 6.64 | 375.42% | 5.93% | 55.56% | 99.94% |