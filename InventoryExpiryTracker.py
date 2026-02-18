'''
Docstring for InventoryExpiryTracker Model

run with: python InventoryExpiryTracker.py

input: inventory.json (sample data provided)

output: test_demo_result_2.json (full result of the analysis)
'''
from datetime import datetime
import json
from typing import Dict, List, Any, Tuple


CRITICAL_THRESHOLD = 7   # days — expires this week
WARNING_THRESHOLD  = 14  # days — expires next week

REQUIRED_FIELDS = ['item_id', 'item_name', 'quantity', 'unit', 'expiry_date']

#validation function to check if the input data is in the correct format and contains all required fields
def validate_item(item: Dict[str, Any], index: int) -> Tuple[bool, str]:
    for field in REQUIRED_FIELDS:
        if field not in item:
            return False, f"Item at index {index} is missing required field: '{field}'"
    
    try:
        qty = float(item['quantity'])
        if qty < 0:
            return False, f"Item '{item.get('item_id')}': quantity must be >= 0"
    except (TypeError, ValueError):
        return False, f"Item '{item.get('item_id')}': quantity is not a valid number"

    if 'purchase_price' in item and item['purchase_price'] is not None:
        try:
            price = float(item['purchase_price'])
            if price < 0:
                return False, f"Item '{item.get('item_id')}': purchase_price must be >= 0"
        except (TypeError, ValueError):
            return False, f"Item '{item.get('item_id')}': purchase_price is not a valid number"
        
    return True, ""


def check_inventory_expiry(inventory_data: Any) -> Dict[str, Any]:
    if isinstance(inventory_data, list):
        inventory_list = inventory_data
        current_date   = datetime.now()
    elif isinstance(inventory_data, dict):
        inventory_list = inventory_data.get('inventory', [])
        if 'current_date' in inventory_data:
            try:
                current_date = datetime.fromisoformat(inventory_data['current_date'])
            except (ValueError, TypeError):
                return {
                    'status': 'error',
                    'message': (
                        f"Invalid current_date format: '{inventory_data['current_date']}'. "
                        "Expected ISO format YYYY-MM-DD."
                    ),
                    'timestamp': datetime.now().isoformat()
                }
        else:
            current_date = datetime.now()
    else:
        return {
            'status': 'error',
            'message': 'inventory_data must be a list or a dict with an "inventory" key.',
            'timestamp': datetime.now().isoformat()
        }
    if not inventory_list:
        return {
            'status': 'error',
            'message': 'Inventory list is empty. Nothing to analyse.',
            'timestamp': current_date.isoformat()
        }

    
    critical_items = []
    warning_items = []
    ok_items      = []
    expired_items = []
    skipped_items = []


    for index, item in enumerate(inventory_list):
        is_valid, error_msg = validate_item(item, index)
        if not is_valid:
            skipped_items.append({
                'item_id': item.get('item_id', f'unknown_index_{index}'),
                'item_name': item.get('item_name', 'unknown'),
                'reason'   : error_msg
            })
            continue
        
        expiry_date_raw = item.get('expiry_date')
        if expiry_date_raw is None:
            skipped_items.append({
                'item_id'  : item['item_id'],
                'item_name': item['item_name'],
                'reason'   : 'No expiry date provided — item excluded from expiry tracking'
            })
            continue

        try:
            expiry_date = datetime.fromisoformat(str(expiry_date_raw))
        except (ValueError, TypeError):
            skipped_items.append({
                'item_id'  : item['item_id'],
                'item_name': item['item_name'],
                'reason'   : f"Invalid expiry_date format: '{expiry_date_raw}'. Expected YYYY-MM-DD."
            })
            continue



        days_until_expiry = (expiry_date - current_date).days

        value_at_risk = round(
            float(item.get('purchase_price') or 0) * float(item.get('quantity') or 0), 2
        )

        enriched_item = {
            'item_id': item['item_id'],
            'item_name': item['item_name'],
            'quantity': item['quantity'],
            'unit': item['unit'],
            'days_until_expiry': days_until_expiry,
            'expiry_date': expiry_date_raw,
            'value_at_risk': value_at_risk
        }

        if days_until_expiry <= 0:
            enriched_item['recommendation'] = "Item has EXPIRED. Remove from stock immediately and do not sell."
            expired_items.append(enriched_item)

        elif days_until_expiry < CRITICAL_THRESHOLD:
            enriched_item['recommendation'] = (
                "Offer 20-30% discount to clear stock immediately. "
                "Contact regular customers directly. "
                "Consider donation if unsellable."
            )
            critical_items.append(enriched_item)

        elif days_until_expiry < WARNING_THRESHOLD:
            enriched_item['recommendation'] = (
                "Feature prominently in store. "
                "Include in meal combos or special offers. "
                "Consider freezing or further processing."
            )
            warning_items.append(enriched_item)

        else:
            enriched_item['recommendation'] = "Monitor regularly — stock is within safe range."
            ok_items.append(enriched_item)
    
    total_value_at_risk = round(sum(
        item['value_at_risk']
        for item in critical_items + warning_items
    ), 2)

    total_expired_value = round(
        sum(item['value_at_risk'] for item in expired_items), 2
    )

    response = {
        'status': 'success',
        'summary': {
            'critical_items': len(critical_items),
            'warning_items': len(warning_items),
            'ok_items': len(ok_items),
            'expired_items': len(expired_items),
            'skipped_items'      : len(skipped_items),
            'total_value_at_risk': (total_value_at_risk),
            'total_expired_value': total_expired_value
        },
        'critical_items': critical_items,
        'warning_items': warning_items,
        'expired_items': expired_items,
        'ok_items': ok_items,
        'skipped_items': skipped_items,
        'timestamp': current_date.isoformat()
    }
    return response

#===========================================
#            MAIN SECTION
#===========================================

if __name__ == '__main__':

    print("="*50)
    print("INVENTORY EXPIRY MODEL - QUICK TEST")
    print("="*50)

    with open('inventory.json', 'r') as f:
        test_data = json.load(f)
    
    result = check_inventory_expiry(test_data)

    if result['status'] == 'error':
        print(f"\n❌ ERROR: {result['message']}")
    else:
        s = result['summary']

        print(f"\n SUMMARY")
        print(f"    Critical:   {s['critical_items']} items")
        print(f"    Warning:    {s['warning_items']} items")
        print(f"    OK:         {s['ok_items']} items")
        print(f"    Expired :   {s['expired_items']} items")
        print(f"   Skipped   : {s['skipped_items']} items (no expiry date or invalid data)")
        print(f"   ⚠ Value At Risk (actionable) : ₦{s['total_value_at_risk']:,.2f}")
        print(f"   💸 Confirmed Losses (expired) : ₦{s['total_expired_value']:,.2f}")


        if result['critical_items']:
            print(f"\n🔴 CRITICAL ITEMS (Action Needed NOW!)")
            print("-"*50)
            for item in result['critical_items']:
                print(f"   • {item['item_name']}")
                print(f"     Expires in: {item['days_until_expiry']} days")
                print(f"     Quantity: {item['quantity']} {item['unit']}")
                print(f"     Value: ₦{item['value_at_risk']:,.2f}")
                print(f"     ➜ {item['recommendation']}")
                print()

        if result['warning_items']:
            print(f"\n⚠️  WARNING ITEMS (Take Action Soon)")
            print("-"*50)
            for item in result['warning_items']:
                print(f"   • {item['item_name']}")
                print(f"     Expires in: {item['days_until_expiry']} days")
                print(f"     Quantity   : {item['quantity']} {item['unit']}")
                print(f"     Value      : ₦{item['value_at_risk']:,.2f}")
                print(f"     ➜ {item['recommendation']}")
                print()

        if result['ok_items']:
            print(f"\n🟢 OKAY ITEMS (Please Monitor Regularly)")
            print("-"*50)
            for item in result['ok_items']:
                print(f"   • {item['item_name']}")
                print(f"     Expires in: {item['days_until_expiry']} days")
                print(f"     Quantity: {item['quantity']} {item['unit']}")
                print(f"     Value: ₦{item['value_at_risk']:,.2f}")
                print(f"     ➜ {item['recommendation']}")
                print()
        
        if result['skipped_items']:
            print(f"\n⬜ SKIPPED ITEMS — No Expiry Date or Invalid Data")
            print("-" * 60)
            for item in result['skipped_items']:
                print(f"   • {item['item_name']}  [{item['item_id']}]")
                print(f"     Reason: {item['reason']}")
                print()

    with open('test_demo_result_2.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("="*50)
    print("✅ Testing complete! Full result saved to: test_demo_result_2.json")
    print("="*50)