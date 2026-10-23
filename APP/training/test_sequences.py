"""Regression checks for length-aware sequence models and seasonal cutoffs."""
import unittest
from datetime import date
import torch
from APP.models.temporal import YieldLSTM, MaskedYieldCNN, YieldCNNLSTM
from APP.training.train_sequences import window


class SequenceTests(unittest.TestCase):
    def test_cross_year_windows(self):
        self.assertEqual(window(2023,'Rabi'),(date(2023,11,1),date(2024,5,1)))
        self.assertEqual(window(2023,'Summer'),(date(2024,3,1),date(2024,7,1)))

    def test_padding_does_not_affect_predictions(self):
        torch.manual_seed(42)
        x=torch.randn(3,20,11); lengths=torch.tensor([7,12,20]); static=torch.randn(3,11)
        changed=x.clone()
        for i,n in enumerate(lengths): changed[i,n:]=1000
        for cls in [YieldLSTM,MaskedYieldCNN,YieldCNNLSTM]:
            model=cls(11,11,32).eval()
            with torch.inference_mode():
                self.assertTrue(torch.allclose(model(x,lengths,static),model(changed,lengths,static),atol=1e-6),cls.__name__)

    def test_all_models_backpropagate(self):
        for cls in [YieldLSTM,MaskedYieldCNN,YieldCNNLSTM]:
            model=cls(11,11,32)
            loss=model(torch.randn(4,13,11),torch.tensor([7,8,10,13]),torch.randn(4,11)).square().mean()
            loss.backward()
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))


if __name__=='__main__': unittest.main()
