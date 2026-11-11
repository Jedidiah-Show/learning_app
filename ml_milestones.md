
# RUACH — Machine Learning Pathway
## Release Milestones and Delivery Roadmap

**Release:** Learning & Engineering Growth
**Pathway:** Machine Learning (ML)
**Status:** Proposed
**Priority:** High
**Primary Objective:** Build a structured, practical, evidence-based Machine Learning learning experience that takes a learner from foundational concepts to developing, evaluating, deploying and maintaining machine learning systems.

---

# 1. Vision

The RUACH Machine Learning pathway should help learners progress from understanding what machine learning is to independently building and deploying meaningful machine learning solutions.

It must not be a collection of disconnected tutorials or a catalogue of algorithms.

It should provide a progressive engineering experience in which learners:

1. Understand the mathematical and statistical foundations of ML.
2. Learn how to acquire, inspect, clean and prepare data.
3. Understand the principles behind machine learning algorithms.
4. Implement and experiment with models.
5. Evaluate models using appropriate metrics.
6. Understand overfitting, underfitting, generalisation and model limitations.
7. Build complete ML projects.
8. Deploy models as usable services.
9. Monitor and maintain deployed models.
10. Develop the engineering judgement required to solve real-world problems.

The pathway should connect theory, implementation, experimentation and practical engineering.

# 2. Guiding Principles

- **Conceptual understanding before memorisation:** Learners should understand why an algorithm works, not merely how to call it.
- **Mathematics without unnecessary intimidation:** Introduce mathematical concepts progressively and connect them to practical applications.
- **Data-first thinking:** Teach learners that data quality, assumptions and problem formulation often matter more than algorithm selection.
- **Experimentation over copying:** Learners must investigate how changing data, features, parameters and algorithms affects outcomes.
- **Evaluation over accuracy alone:** Teach learners to choose metrics based on the actual problem.
- **Engineering from the beginning:** Introduce reproducibility, version control, testing, documentation and responsible data handling.
- **Evidence-based progression:** Skills should be demonstrated through practical work, not simply lesson completion.
- **Progressive independence:** Reduce scaffolding as learners become more competent.

# 3. Milestones

## M0 — ML Pathway Foundations and Architecture

**Goal:** Establish the learning structure, curriculum model, technical prerequisites and assessment standards for the ML pathway.

### Deliverables

- Dedicated Machine Learning learning path.
- ML competency framework.
- Curriculum hierarchy and prerequisite relationships.
- ML-specific lesson and exercise metadata.
- Learning objectives for every module.
- Defined assessment and completion criteria.
- ML project progression model.
- Integration with the shared RUACH learning infrastructure.

### Competency domains

- Mathematics and statistics.
- Python for data science.
- Data manipulation and analysis.
- Data preparation and feature engineering.
- Supervised learning.
- Unsupervised learning.
- Model evaluation and optimisation.
- Deep learning foundations.
- ML deployment.
- MLOps and production systems.

### Acceptance criteria

- The ML pathway is independently identifiable from AI Engineering.
- Each module has measurable learning objectives.
- Prerequisites are defined and enforceable.
- Learners can identify their current learning stage.
- ML-specific progress is not incorrectly counted as AI Engineering progress.

---

## M1 — Mathematical and Statistical Foundations

**Goal:** Give learners sufficient mathematical and statistical understanding to reason about machine learning algorithms.

### Curriculum areas

**Mathematics**
- Arithmetic and algebra refreshers.
- Functions and graphs.
- Vectors and matrices.
- Matrix operations.
- Dot products.
- Linear transformations.
- Derivatives and gradients.
- Partial derivatives.
- Gradient descent intuition.

**Statistics and probability**
- Descriptive statistics.
- Mean, median and mode.
- Variance and standard deviation.
- Probability fundamentals.
- Conditional probability.
- Probability distributions.
- Sampling.
- Correlation and covariance.
- Statistical inference.
- Hypothesis testing.
- Confidence intervals.

### Practical activities

- Calculate descriptive statistics from datasets.
- Visualise distributions.
- Investigate correlation.
- Explore probability through simulations.
- Implement simple gradient descent.
- Observe how learning rates affect optimisation.

### Acceptance criteria

- Learners can explain relevant mathematical concepts in plain language.
- Learners can perform foundational statistical calculations.
- Learners can interpret common distributions and statistical summaries.
- Learners can explain the intuition behind gradient descent.
- Practical exercises connect mathematical concepts to ML applications.

---

## M2 — Python, Data Analysis and Data Preparation

**Goal:** Develop the ability to work with real-world datasets and prepare data for machine learning.

### Curriculum areas

**Python foundations**
- Python programming fundamentals.
- Functions and modules.
- Data structures.
- File handling.
- Exceptions.
- Working with packages and environments.

**Data science tools**
- NumPy.
- Pandas.
- Matplotlib.
- Seaborn.

**Data preparation**
- Loading datasets.
- Understanding dataset structure.
- Data types.
- Missing values.
- Duplicate records.
- Outlier investigation.
- Data transformations.
- Encoding categorical variables.
- Feature scaling.
- Feature selection.
- Data leakage.
- Train, validation and test splits.

### Practical activities

- Explore CSV datasets.
- Perform exploratory data analysis.
- Clean incomplete datasets.
- Visualise relationships between variables.
- Build reusable preprocessing workflows.
- Compare raw and transformed datasets.

### Acceptance criteria

- Learners can independently inspect and prepare datasets.
- Learners can identify common data-quality problems.
- Learners understand why preprocessing decisions matter.
- Learners can explain data leakage and how to prevent it.
- Data preparation work is reproducible.

---

## M3 — Supervised Machine Learning

**Goal:** Teach learners how to formulate supervised learning problems, train models and interpret their results.

### Curriculum areas

**Core concepts**
- What is supervised learning?
- Features and labels.
- Regression versus classification.
- Training and prediction.
- Model assumptions.
- Bias and variance.
- Underfitting and overfitting.
- Generalisation.

**Regression**
- Simple linear regression.
- Multiple linear regression.
- Polynomial regression.
- Regularisation.
- Ridge and Lasso regression.

**Classification**
- Logistic regression.
- K-nearest neighbours.
- Decision trees.
- Random forests.
- Support vector machines.
- Naive Bayes.
- Ensemble learning foundations.

### Practical activities

- Predict house prices.
- Predict customer churn.
- Classify customer transactions.
- Compare regression algorithms.
- Compare classification algorithms.
- Investigate model complexity.
- Experiment with regularisation.

### Acceptance criteria

- Learners can identify regression and classification problems.
- Learners can train models using appropriate datasets.
- Learners can explain model predictions at a foundational level.
- Learners can identify overfitting and underfitting.
- Learners can compare multiple algorithms meaningfully.

---

## M4 — Model Evaluation, Optimisation and Experimentation

**Goal:** Develop sound model evaluation and experimentation practices.

### Curriculum areas

**Regression metrics**
- MAE.
- MSE.
- RMSE.
- R-squared.

**Classification metrics**
- Accuracy.
- Precision.
- Recall.
- F1-score.
- Confusion matrix.
- ROC curve.
- AUC.
- Precision-recall curves.

**Validation techniques**
- Train/test split.
- Validation sets.
- K-fold cross-validation.
- Stratified sampling.

**Optimisation**
- Hyperparameter tuning.
- Grid search.
- Random search.
- Learning curves.
- Model comparison.
- Threshold selection.
- Error analysis.

**Responsible evaluation**
- Class imbalance.
- Data leakage.
- Sampling bias.
- Fairness considerations.
- Model limitations.

### Practical activities

- Evaluate multiple models on the same dataset.
- Investigate the consequences of using accuracy alone.
- Compare precision and recall trade-offs.
- Perform cross-validation.
- Tune model hyperparameters.
- Document experiments and conclusions.

### Acceptance criteria

- Learners select metrics appropriate to the problem.
- Learners understand the difference between training and test performance.
- Learners can identify common evaluation mistakes.
- Learners can explain why one model was selected over another.
- Experiments are documented and reproducible.

---

## M5 — Unsupervised Learning and Feature Engineering

**Goal:** Introduce methods for discovering patterns and useful representations in data without relying on labelled outcomes.

### Curriculum areas

**Unsupervised learning**
- Clustering fundamentals.
- K-means.
- Hierarchical clustering.
- DBSCAN.
- Dimensionality reduction.
- Principal Component Analysis.
- Anomaly detection.

**Feature engineering**
- Feature creation.
- Feature transformation.
- Feature selection.
- Interaction features.
- Domain-driven features.
- Dimensionality considerations.

### Practical activities

- Customer segmentation.
- Transaction anomaly detection.
- Visualising high-dimensional datasets.
- Comparing clustering approaches.
- Applying PCA.
- Evaluating the usefulness of engineered features.

### Acceptance criteria

- Learners can distinguish supervised and unsupervised learning.
- Learners can apply foundational clustering techniques.
- Learners understand the purpose and limitations of dimensionality reduction.
- Learners can investigate whether engineered features improve a model.

---

## M6 — Deep Learning Foundations

**Goal:** Introduce neural networks and establish the foundations required to understand modern deep learning systems.

### Curriculum areas

- Artificial neurons.
- Neural network architecture.
- Activation functions.
- Forward propagation.
- Loss functions.
- Backpropagation.
- Gradient-based optimisation.
- Learning rates.
- Batch sizes.
- Epochs.
- Regularisation.
- Dropout.
- Neural network evaluation.

**Frameworks**
- PyTorch or TensorFlow/Keras.
- Tensor operations.
- Model definition.
- Training loops.
- Validation.
- Model saving and loading.

**Further topics**
- Convolutional neural network fundamentals.
- Recurrent network concepts.
- Transformer architecture overview.
- Transfer learning.
- Fine-tuning foundations.

### Practical activities

- Implement a simple neural network.
- Train a model on a classification dataset.
- Investigate loss curves.
- Compare optimisers.
- Experiment with model architecture.
- Build a basic image classifier.

### Acceptance criteria

- Learners understand the basic components of neural networks.
- Learners can train and evaluate a neural network.
- Learners can interpret loss and learning curves.
- Learners can explain the role of backpropagation.
- Learners understand when deep learning is and is not appropriate.

---

## M7 — ML Engineering and Deployment

**Goal:** Move beyond notebooks and teach learners how to turn trained models into usable software.

### Curriculum areas

- Reproducible ML environments.
- Model serialisation.
- Model loading.
- REST APIs for inference.
- FastAPI foundations.
- Input validation.
- Prediction services.
- Batch versus online inference.
- Model versioning.
- Docker fundamentals.
- Deployment environments.
- Logging and error handling.
- Testing ML services.

### Practical activities

- Package a trained model.
- Build a prediction API.
- Validate incoming requests.
- Containerise an ML application.
- Deploy a model service.
- Test inference endpoints.

### Acceptance criteria

- Learners can expose a trained model through an API.
- Models can be loaded and used outside the training notebook.
- The service validates input and handles errors.
- The application can be containerised.
- Deployment instructions are documented.

---

## M8 — MLOps, Monitoring and Production ML

**Goal:** Introduce the practices required to maintain reliable machine learning systems.

### Curriculum areas

- ML lifecycle management.
- Experiment tracking.
- Dataset versioning.
- Model versioning.
- Training pipelines.
- Model registries.
- CI/CD for ML.
- Model monitoring.
- Data drift.
- Concept drift.
- Model performance degradation.
- Retraining strategies.
- Model governance.
- Reproducibility.
- Monitoring and observability.

**Suggested tools**
- MLflow.
- DVC.
- Docker.
- GitHub Actions.
- Evidently AI.
- Cloud ML services where appropriate.

### Practical activities

- Track model experiments.
- Version datasets.
- Register model versions.
- Build a reproducible training pipeline.
- Monitor data and prediction drift.
- Simulate model degradation.
- Design a retraining workflow.

### Acceptance criteria

- Learners understand the ML lifecycle after deployment.
- Experiments and models are traceable.
- Learners can explain data drift and concept drift.
- Learners can implement foundational monitoring.
- Learners understand the purpose of automated retraining and its risks.

---

## M9 — Capstone, Portfolio and Skill Passport

**Goal:** Demonstrate independent ML engineering capability through complete projects.

### Required capstone stages

1. Problem identification.
2. Problem formulation.
3. Dataset selection and understanding.
4. Exploratory data analysis.
5. Data preparation.
6. Feature engineering.
7. Baseline model.
8. Model experimentation.
9. Evaluation and error analysis.
10. Model selection.
11. Deployment.
12. Documentation.
13. Limitations and responsible-use assessment.

### Suggested capstone projects

- Customer churn prediction.
- Loan default risk prediction.
- House price prediction.
- Fraud or anomaly detection.
- Customer segmentation.
- Demand forecasting.
- Image classification.
- Predictive maintenance.

### Acceptance criteria

- Project addresses a clearly defined problem.
- Dataset and preprocessing decisions are documented.
- Multiple experiments are recorded.
- Evaluation uses appropriate metrics.
- Model limitations are acknowledged.
- A usable deployment or inference interface is provided.
- Work is added to the learner's Skill Passport.
- The learner can explain and defend their engineering decisions.

# 4. Cross-Pathway Integration

The ML pathway must integrate with shared RUACH services without becoming dependent on AI Engineering content.

| Shared feature | ML pathway application |
|---|---|
| Practice Arena | ML concepts, Python, statistics, data preparation, algorithms and model evaluation challenges |
| Learning Path | ML-specific modules, prerequisites and progression |
| Skill Passport | Evidence of demonstrated ML competencies |
| AI Tutor 2.0 | Mathematical explanations, model debugging, conceptual guidance and experiment interpretation |
| Project Studio | Guided ML projects with milestones and evidence |
| Engineering Labs | Dataset debugging, training failures, deployment and monitoring scenarios |

# 5. Release Completion Conditions

The ML pathway should not be considered complete merely because all lessons are published.

Release acceptance requires:

- A coherent curriculum with prerequisites.
- Working ML-specific exercises.
- Meaningful practical assessments.
- At least one complete beginner ML project.
- At least one intermediate ML project.
- ML-aware tutoring.
- ML project support in Project Studio.
- Evidence-based Skill Passport progression.
- Documented deployment and MLOps learning experiences.
- Security, accessibility and reliability verification.

# 6. Definition of Success

A learner who completes the foundational and intermediate ML pathway should be able to independently:

- Formulate a machine learning problem.
- Inspect and prepare a dataset.
- Select a suitable baseline algorithm.
- Train and evaluate a model.
- Explain evaluation results.
- Investigate model errors.
- Improve model performance through justified experimentation.
- Package a model for inference.
- Expose the model through an API.
- Explain foundational MLOps practices.

The objective is not to make learners memorise algorithms. It is to develop people who can reason about data, models and the engineering systems that support them.
