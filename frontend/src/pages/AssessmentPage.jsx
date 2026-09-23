import PredictionForm from "../components/PredictionForm";
import PredictionResult from "../components/PredictionResult";

export default function AssessmentPage({ result, onPrediction, onReset, formKey }) {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">JATAYU · Risk intelligence</p>
        <h1>Credit card default assessment</h1>
        <p>Enter the customer ID and current-month activity for a real-time default-risk prediction.</p>
      </section>
      {result && <div className="customer-banner">Customer ID: <strong>{result.customer_code}</strong> · Prediction #{result.prediction_id}</div>}
      <PredictionResult result={result} onReset={onReset} />
      <PredictionForm key={formKey} onPrediction={onPrediction} />
    </main>
  );
}
