import { useEffect, useMemo, useState } from 'react';

const API_URL = 'http://localhost:8000/api';

const emptyItem = () => ({ description: '', quantity: 1, unit_price: 0 });

function App() {
  const [dashboard, setDashboard] = useState({
    customers_count: 0,
    invoices_count: 0,
    total_revenue: 0,
    outstanding: 0,
    overdue_count: 0,
  });
  const [customers, setCustomers] = useState([]);
  const [invoices, setInvoices] = useState([]);

  const [customerForm, setCustomerForm] = useState({
    name: '',
    email: '',
    company: '',
  });

  const [invoiceForm, setInvoiceForm] = useState({
    customer_id: '',
    tax_rate: 10,
    due_days: 14,
    items: [emptyItem()],
  });

  const loadData = async () => {
    try {
      const [customersRes, invoicesRes, dashboardRes] = await Promise.all([
        fetch(`${API_URL}/customers`),
        fetch(`${API_URL}/invoices`),
        fetch(`${API_URL}/dashboard`),
      ]);

      const customersData = await customersRes.json();
      const invoicesData = await invoicesRes.json();
      const dashboardData = await dashboardRes.json();

      setCustomers(customersData);
      setInvoices(invoicesData);
      setDashboard(dashboardData);

      if (customersData.length && !invoiceForm.customer_id) {
        setInvoiceForm((current) => ({ ...current, customer_id: String(customersData[0].id) }));
      }
    } catch (error) {
      console.error('Failed to load billing data', error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const addItem = () => {
    setInvoiceForm((current) => ({
      ...current,
      items: [...current.items, emptyItem()],
    }));
  };

  const updateItem = (index, field, value) => {
    setInvoiceForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: field === 'quantity' || field === 'unit_price' ? Number(value) : value } : item
      ),
    }));
  };

  const removeItem = (index) => {
    setInvoiceForm((current) => ({
      ...current,
      items: current.items.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const handleCustomerSubmit = async (event) => {
    event.preventDefault();

    const response = await fetch(`${API_URL}/customers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(customerForm),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(error.detail || 'Unable to create customer');
      return;
    }

    setCustomerForm({ name: '', email: '', company: '' });
    loadData();
  };

  const handleInvoiceSubmit = async (event) => {
    event.preventDefault();

    const payload = {
      customer_id: Number(invoiceForm.customer_id),
      due_days: Number(invoiceForm.due_days),
      tax_rate: Number(invoiceForm.tax_rate),
      items: invoiceForm.items
        .filter((item) => item.description.trim())
        .map((item) => ({
          description: item.description,
          quantity: Number(item.quantity),
          unit_price: Number(item.unit_price),
        })),
    };

    if (!payload.items.length) {
      alert('Please add at least one invoice item.');
      return;
    }

    const response = await fetch(`${API_URL}/invoices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(error.detail || 'Unable to create invoice');
      return;
    }

    setInvoiceForm({
      customer_id: customers[0] ? String(customers[0].id) : '',
      tax_rate: 10,
      due_days: 14,
      items: [emptyItem()],
    });
    loadData();
  };

  const handlePayment = async (invoiceId) => {
    const amountInput = document.getElementById(`payment-${invoiceId}`);
    if (!amountInput || !Number(amountInput.value)) {
      alert('Enter a valid payment amount');
      return;
    }

    const response = await fetch(`${API_URL}/invoices/${invoiceId}/pay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount: Number(amountInput.value),
        method: 'card',
        reference: `web-${Date.now()}`,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      alert(error.detail || 'Payment failed');
      return;
    }

    amountInput.value = '';
    loadData();
  };

  const totalDue = useMemo(
    () => invoices.reduce((sum, invoice) => sum + (invoice.total - invoice.paid_amount), 0),
    [invoices]
  );

  return (
    <div className="app">
      <header className="topbar">
        <h1>Billing Dashboard</h1>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Customers</span>
          <div className="stat-value">{dashboard.customers_count}</div>
        </div>
        <div className="stat-card">
          <span className="stat-label">Invoices</span>
          <div className="stat-value">{dashboard.invoices_count}</div>
        </div>
        <div className="stat-card">
          <span className="stat-label">Revenue</span>
          <div className="stat-value">${dashboard.total_revenue.toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <span className="stat-label">Outstanding</span>
          <div className="stat-value">${dashboard.outstanding.toFixed(2)}</div>
        </div>
        <div className="stat-card">
          <span className="stat-label">Overdue</span>
          <div className="stat-value">{dashboard.overdue_count}</div>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel">
          <h2>Create Customer</h2>
          <form className="form-grid" onSubmit={handleCustomerSubmit}>
            <input
              placeholder="Full name"
              value={customerForm.name}
              onChange={(event) => setCustomerForm({ ...customerForm, name: event.target.value })}
              required
            />
            <input
              placeholder="Email"
              type="email"
              value={customerForm.email}
              onChange={(event) => setCustomerForm({ ...customerForm, email: event.target.value })}
              required
            />
            <input
              placeholder="Company"
              value={customerForm.company}
              onChange={(event) => setCustomerForm({ ...customerForm, company: event.target.value })}
            />
            <button className="primary" type="submit">Add Customer</button>
          </form>

          <hr style={{ margin: '24px 0' }} />

          <h2>Create Invoice</h2>
          <form className="form-grid" onSubmit={handleInvoiceSubmit}>
            <select
              value={invoiceForm.customer_id}
              onChange={(event) => setInvoiceForm({ ...invoiceForm, customer_id: event.target.value })}
            >
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>

            <div className="form-row">
              <input
                type="number"
                min="0"
                value={invoiceForm.tax_rate}
                onChange={(event) => setInvoiceForm({ ...invoiceForm, tax_rate: Number(event.target.value) })}
                placeholder="Tax rate %"
              />
              <input
                type="number"
                min="1"
                value={invoiceForm.due_days}
                onChange={(event) => setInvoiceForm({ ...invoiceForm, due_days: Number(event.target.value) })}
                placeholder="Due days"
              />
            </div>

            {invoiceForm.items.map((item, index) => (
              <div key={index} className="item-row">
                <input
                  value={item.description}
                  onChange={(event) => updateItem(index, 'description', event.target.value)}
                  placeholder="Description"
                />
                <input
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(event) => updateItem(index, 'quantity', event.target.value)}
                />
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.unit_price}
                  onChange={(event) => updateItem(index, 'unit_price', event.target.value)}
                />
                <button type="button" className="secondary" onClick={() => removeItem(index)}>
                  Remove
                </button>
              </div>
            ))}

            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="secondary" onClick={addItem}>Add Item</button>
              <button type="submit" className="primary">Save Invoice</button>
            </div>
          </form>
        </div>

        <div className="panel">
          <h2>Invoices</h2>
          <div className="invoice-list">
            {invoices.length === 0 ? (
              <div className="empty-state">No invoices yet.</div>
            ) : (
              invoices.map((invoice) => {
                const customer = customers.find((item) => item.id === invoice.customer_id);
                const remaining = Math.max(invoice.total - invoice.paid_amount, 0);
                const badgeClass =
                  invoice.status === 'paid' ? 'success' : invoice.status === 'partially_paid' ? 'warning' : 'neutral';

                return (
                  <div key={invoice.id} className="invoice-card">
                    <div className="invoice-header">
                      <div>
                        <strong>INV-{invoice.id}</strong>
                        <div className="invoice-meta">
                          <span>{customer ? customer.name : 'Unknown customer'}</span>
                          <span>Due: {new Date(invoice.due_date).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <span className={`badge ${badgeClass}`}>{invoice.status}</span>
                    </div>

                    <div className="summary-row"><span>Subtotal</span><strong>${invoice.subtotal.toFixed(2)}</strong></div>
                    <div className="summary-row"><span>Tax</span><strong>${invoice.tax_amount.toFixed(2)}</strong></div>
                    <div className="summary-row"><span>Total</span><strong>${invoice.total.toFixed(2)}</strong></div>
                    <div className="summary-row"><span>Paid</span><strong>${invoice.paid_amount.toFixed(2)}</strong></div>
                    <div className="summary-row"><span>Remaining</span><strong>${remaining.toFixed(2)}</strong></div>

                    <div className="payment-form">
                      <input id={`payment-${invoice.id}`} type="number" step="0.01" placeholder="Payment amount" />
                      <button type="button" className="primary" onClick={() => handlePayment(invoice.id)}>
                        Pay
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;
