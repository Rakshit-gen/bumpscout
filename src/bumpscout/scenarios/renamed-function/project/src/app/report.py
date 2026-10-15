from tablet import render_table


def sales_report(sales):
    rows = [("region", "total")] + [(k, v) for k, v in sorted(sales.items())]
    return render_table(rows)
