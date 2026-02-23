"""
CALIBRATION - Model quality metrics
=====================================

Measures how well the prediction model's probabilities match reality:
- Brier Score: mean squared error (lower = better, <0.25 is decent for football)
- Log-Loss: penalizes confident wrong predictions
- Calibration bins: when we say 60%, do teams win ~60% of the time?
"""

import math


def brier_score(predictions_with_results: list) -> dict:
    """
    Calculate Brier Score for 1X2 predictions.
    
    Brier = mean( (predicted_prob - actual_outcome)^2 )
    Perfect = 0.0, Random = 0.5, Always 33% = 0.222
    
    Args:
        predictions_with_results: list of dicts with pred_home_win, pred_draw, 
                                  pred_away_win, home_goals, away_goals
    Returns:
        Dict with overall Brier score and per-market breakdown
    """
    if not predictions_with_results:
        return {'brier': None, 'n': 0}
    
    total_brier = 0.0
    n = 0
    
    for p in predictions_with_results:
        hg = p.get('home_goals')
        ag = p.get('away_goals')
        
        if hg is None or ag is None:
            continue
        if p.get('pred_home_win') is None:
            continue
        
        # Actual outcome as one-hot vector
        if hg > ag:
            actual = [1, 0, 0]  # Home win
        elif hg == ag:
            actual = [0, 1, 0]  # Draw
        else:
            actual = [0, 0, 1]  # Away win
        
        predicted = [
            p['pred_home_win'],
            p['pred_draw'],
            p['pred_away_win'],
        ]
        
        # Brier score for this match (multi-class)
        match_brier = sum((pred - act) ** 2 for pred, act in zip(predicted, actual))
        total_brier += match_brier
        n += 1
    
    return {
        'brier': total_brier / n if n > 0 else None,
        'n': n,
    }


def log_loss(predictions_with_results: list) -> dict:
    """
    Calculate log-loss for 1X2 predictions.
    
    Log-loss = -mean( actual × log(predicted) )
    Heavily penalizes confident wrong predictions.
    """
    if not predictions_with_results:
        return {'log_loss': None, 'n': 0}
    
    total_ll = 0.0
    n = 0
    eps = 1e-10  # Prevent log(0)
    
    for p in predictions_with_results:
        hg = p.get('home_goals')
        ag = p.get('away_goals')
        
        if hg is None or ag is None:
            continue
        if p.get('pred_home_win') is None:
            continue
        
        if hg > ag:
            prob = max(eps, p['pred_home_win'])
        elif hg == ag:
            prob = max(eps, p['pred_draw'])
        else:
            prob = max(eps, p['pred_away_win'])
        
        total_ll -= math.log(prob)
        n += 1
    
    return {
        'log_loss': total_ll / n if n > 0 else None,
        'n': n,
    }


def calibration_bins(predictions_with_results: list, n_bins: int = 5) -> list:
    """
    Group predictions by confidence level and check actual win rate.
    
    Returns list of bins: [{range, predicted_avg, actual_avg, count}]
    """
    # Collect all (predicted_prob, actual_outcome) pairs for all markets
    pairs = []
    
    for p in predictions_with_results:
        hg = p.get('home_goals')
        ag = p.get('away_goals')
        if hg is None or ag is None or p.get('pred_home_win') is None:
            continue
        
        # Home win
        pairs.append((p['pred_home_win'], 1 if hg > ag else 0))
        # Draw
        pairs.append((p['pred_draw'], 1 if hg == ag else 0))
        # Away win
        pairs.append((p['pred_away_win'], 1 if hg < ag else 0))
    
    if not pairs:
        return []
    
    # Sort by predicted probability
    pairs.sort(key=lambda x: x[0])
    
    # Split into bins
    bin_size = len(pairs) // n_bins
    bins = []
    
    for i in range(n_bins):
        start = i * bin_size
        end = start + bin_size if i < n_bins - 1 else len(pairs)
        chunk = pairs[start:end]
        
        if not chunk:
            continue
        
        pred_avg = sum(p for p, _ in chunk) / len(chunk)
        actual_avg = sum(a for _, a in chunk) / len(chunk)
        
        bins.append({
            'range': f"{chunk[0][0]:.0%}-{chunk[-1][0]:.0%}",
            'predicted': round(pred_avg, 3),
            'actual': round(actual_avg, 3),
            'count': len(chunk),
            'gap': round(pred_avg - actual_avg, 3),
        })
    
    return bins


def generate_report(match_history) -> str:
    """Generate a calibration report string."""
    data = match_history.get_predictions_with_results()
    
    if not data:
        return "📊 No predictions with results yet. Run the model for a few days first."
    
    bs = brier_score(data)
    ll = log_loss(data)
    bins = calibration_bins(data)
    
    lines = []
    lines.append("=" * 60)
    lines.append("   📊 MODEL CALIBRATION REPORT")
    lines.append("=" * 60)
    lines.append(f"   Predictions evaluated: {bs['n']}")
    lines.append("")
    
    # Brier score interpretation
    if bs['brier'] is not None:
        quality = (
            "🟢 Excellent" if bs['brier'] < 0.20 else
            "🟡 Good" if bs['brier'] < 0.22 else
            "🟠 Average" if bs['brier'] < 0.25 else
            "🔴 Poor"
        )
        lines.append(f"   Brier Score:  {bs['brier']:.4f}  {quality}")
        lines.append(f"   (Perfect=0.00, Random=0.50, Always-33%=0.22)")
    
    if ll['log_loss'] is not None:
        lines.append(f"   Log-Loss:     {ll['log_loss']:.4f}")
    
    lines.append("")
    lines.append("   Calibration (predicted vs actual):")
    lines.append(f"   {'Bin':<12} {'Predicted':>10} {'Actual':>10} {'Gap':>8} {'Count':>6}")
    lines.append("   " + "-" * 50)
    
    for b in bins:
        gap_str = f"{b['gap']:+.1%}"
        emoji = "✅" if abs(b['gap']) < 0.05 else "⚠️" if abs(b['gap']) < 0.10 else "❌"
        lines.append(
            f"   {b['range']:<12} {b['predicted']:>10.1%} {b['actual']:>10.1%} "
            f"{gap_str:>8} {b['count']:>5} {emoji}"
        )
    
    lines.append("")
    lines.append("   ✅ = well calibrated (<5% gap)")
    lines.append("   ⚠️  = slight miscalibration (5-10%)")
    lines.append("   ❌ = significant miscalibration (>10%)")
    lines.append("=" * 60)
    
    return "\n".join(lines)
